import io
import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from PIL import Image

try:
    import torch
    import torchvision.transforms as transforms
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    transforms = None
    TORCH_AVAILABLE = False

from app.services.xai.explanation_model import (
    VisionHeatmapExplanation,
    XAICapabilityStatus
)
from app.services.vision.crop_registry import CropModelRegistry
from app.services.vision.provider_contract import VisionModelProvider
from app.services.vision.quality_gate import ImageQualityGate

logger = logging.getLogger(__name__)


class DiseaseGradCAMExplainer:
    """
    Authentic Deep Learning Grad-CAM Explainer for Plant Leaf Pathology.
    Hooks into convolutional feature layers of genuine PyTorch MobileNetV3 architectures.
    Strictly forbids random heatmaps, decorative masks, or faked attributions.
    """

    @classmethod
    def explain_leaf_diagnosis(
        cls,
        image_bytes: bytes,
        crop_hint: Optional[str] = "tomato",
        target_class_idx: Optional[int] = None
    ) -> VisionHeatmapExplanation:
        """
        Generates genuine Grad-CAM heatmap for a leaf diagnosis if supported by the model architecture.
        If unsupported, heuristic, or model weights unavailable, returns UNAVAILABLE_FOR_CURRENT_MODEL.
        """
        # 1. Check PyTorch availability
        if not TORCH_AVAILABLE:
            return VisionHeatmapExplanation(
                predicted_disease="UNKNOWN",
                model_identifier="pytorch_unavailable",
                model_version="none",
                target_class="none",
                heatmap=None,
                xai_status=XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value,
                limitations=["PyTorch deep learning runtime is not available in current environment."]
            )

        # 2. Check Image Quality Gate first
        gate_res = ImageQualityGate.validate(image_bytes)
        if not gate_res.is_valid:
            return VisionHeatmapExplanation(
                predicted_disease="QUALITY_CHECK_FAILED",
                model_identifier="image_quality_gate",
                model_version="v2.0-production",
                target_class="none",
                heatmap=None,
                confidence=0.0,
                xai_status=XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value,
                limitations=[f"Image quality gate failed: {gate_res.reason}. Grad-CAM cannot be computed on degraded input."]
            )

        # 3. Resolve Crop Provider
        canonical_crop = CropModelRegistry.normalize_crop_name(crop_hint) or "tomato"
        provider: Optional[VisionModelProvider] = CropModelRegistry.get_provider(canonical_crop)
        if not provider:
            return VisionHeatmapExplanation(
                predicted_disease="UNSUPPORTED_CROP",
                model_identifier="crop_model_registry",
                model_version="none",
                target_class="none",
                heatmap=None,
                xai_status=XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value,
                limitations=[f"No registered deep learning pathology model for crop '{canonical_crop}'."]
            )

        # 4. Check if underlying model is a genuine differentiable PyTorch Module with Conv layers
        model = getattr(provider, "model", None)
        is_loaded = getattr(provider, "is_loaded", False)

        if model is None or not is_loaded or not isinstance(model, torch.nn.Module):
            return VisionHeatmapExplanation(
                predicted_disease="MODEL_NOT_DIFFERENTIABLE",
                model_identifier=provider.get_crop_name(),
                model_version=provider.get_model_version(),
                target_class="none",
                heatmap=None,
                xai_status=XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value,
                limitations=["Underlying model is not a differentiable PyTorch module with accessible convolutional layers."]
            )

        # Find target convolutional layer (for MobileNetV3, model.features[-1])
        target_layer = None
        if hasattr(model, "features") and len(model.features) > 0:
            target_layer = model.features[-1]
        elif hasattr(model, "conv"):
            target_layer = model.conv

        if target_layer is None:
            return VisionHeatmapExplanation(
                predicted_disease="UNSUPPORTED_LAYER_STRUCTURE",
                model_identifier=provider.get_crop_name(),
                model_version=provider.get_model_version(),
                target_class="none",
                heatmap=None,
                xai_status=XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value,
                limitations=["Architecture does not expose standard convolutional feature map layers for Grad-CAM."]
            )

        # 5. Execute Authentic Grad-CAM Forward & Backward Hooks
        activations: List[torch.Tensor] = []
        gradients: List[torch.Tensor] = []

        def forward_hook(module, inp, out):
            activations.append(out)

        def backward_hook(module, grad_in, grad_out):
            gradients.append(grad_out[0])

        handle_fwd = target_layer.register_forward_hook(forward_hook)
        handle_bwd = target_layer.register_full_backward_hook(backward_hook)

        try:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            transform = getattr(provider, "transform", None)
            if transform is None:
                transform = transforms.Compose([
                    transforms.Resize((224, 224)),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                ])

            input_tensor = transform(pil_img).unsqueeze(0)
            input_tensor.requires_grad = True

            # Model forward
            model.zero_grad()
            logits = model(input_tensor)

            # Determine target class and legitimate confidence
            probs = torch.softmax(logits, dim=-1)[0]
            if target_class_idx is None:
                target_class_idx = int(torch.argmax(probs).item())

            target_prob = float(probs[target_class_idx].item())
            labels_dict = getattr(provider, "labels", {})
            target_label = labels_dict.get(target_class_idx, f"class_{target_class_idx}")

            # Backward pass on target class logit
            score = logits[0, target_class_idx]
            score.backward()

            if not activations or not gradients:
                raise RuntimeError("Grad-CAM hooks failed to capture activations or gradients.")

            act = activations[0].detach()  # [1, C, H, W]
            grad = gradients[0].detach()   # [1, C, H, W]

            # Global average pooling on gradients -> channel weights alpha
            alpha = grad.mean(dim=(2, 3), keepdim=True)  # [1, C, 1, 1]

            # Weighted linear combination of activation maps
            cam = (alpha * act).sum(dim=1, keepdim=True)  # [1, 1, H, W]
            cam = torch.relu(cam)

            cam_min = float(cam.min().item())
            cam_max = float(cam.max().item())
            if cam_max > cam_min:
                cam = (cam - cam_min) / (cam_max - cam_min)
            else:
                cam = torch.zeros_like(cam)

            cam_grid = cam.squeeze().cpu().numpy()  # e.g. [7, 7]
            heatmap_list = [[float(round(v, 4)) for v in row] for row in cam_grid]

            # Compute localization metadata
            peak_indices = np.unravel_index(np.argmax(cam_grid), cam_grid.shape)
            peak_y, peak_x = int(peak_indices[0]), int(peak_indices[1])

            # High activation bounding box in relative coordinates [0.0, 1.0]
            high_mask = cam_grid >= 0.5
            h_grid, w_grid = cam_grid.shape
            high_ratio = float(np.mean(high_mask))

            if np.any(high_mask):
                y_coords, x_coords = np.where(high_mask)
                bbox = {
                    "ymin": round(float(y_coords.min()) / h_grid, 3),
                    "xmin": round(float(x_coords.min()) / w_grid, 3),
                    "ymax": round(float(y_coords.max() + 1) / h_grid, 3),
                    "xmax": round(float(x_coords.max() + 1) / w_grid, 3),
                }
            else:
                bbox = {
                    "ymin": round(peak_y / h_grid, 3),
                    "xmin": round(peak_x / w_grid, 3),
                    "ymax": round((peak_y + 1) / h_grid, 3),
                    "xmax": round((peak_x + 1) / w_grid, 3),
                }

            localization_meta = {
                "peak_cell": [peak_y, peak_x],
                "grid_dimensions": [h_grid, w_grid],
                "bounding_box_normalized": bbox,
                "high_activation_area_ratio": round(high_ratio, 3),
                "mean_activation": round(float(np.mean(cam_grid)), 4),
                "layer_name": target_layer.__class__.__name__
            }

            return VisionHeatmapExplanation(
                predicted_disease=target_label,
                model_identifier=provider.get_crop_name(),
                model_version=provider.get_model_version(),
                target_class=target_label,
                heatmap=heatmap_list,
                heatmap_dimensions=[h_grid, w_grid],
                localization_metadata=localization_meta,
                confidence=round(target_prob, 4),
                xai_status=XAICapabilityStatus.AVAILABLE.value,
                limitations=[]
            )

        except Exception as e:
            logger.error(f"[GRADCAM] Failed to compute Grad-CAM for {canonical_crop}: {e}")
            return VisionHeatmapExplanation(
                predicted_disease="GRADCAM_COMPUTATION_FAILED",
                model_identifier=provider.get_crop_name(),
                model_version=provider.get_model_version(),
                target_class="none",
                heatmap=None,
                xai_status=XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value,
                limitations=[f"Grad-CAM execution exception: {str(e)}"]
            )
        finally:
            handle_fwd.remove()
            handle_bwd.remove()
