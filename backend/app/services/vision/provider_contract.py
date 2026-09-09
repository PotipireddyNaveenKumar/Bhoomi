import os
import io
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

import torch
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image

from app.schemas.vision import VisionPrediction, VisionTopPrediction
from app.services.vision.validator import VisionPredictionValidator
from app.services.vision.quality_gate import ImageQualityGate, ImageQualityGateResult

logger = logging.getLogger(__name__)

class VisionModelProvider(ABC):
    """
    Common contract for all crop vision models.
    Every crop diagnostic model MUST implement this interface and return
    the normalized VisionPrediction schema.
    """
    @abstractmethod
    def get_crop_name(self) -> str:
        """Returns the canonical crop identifier (e.g. 'tomato', 'chilli', 'rice')."""
        pass

    @abstractmethod
    def get_model_version(self) -> str:
        """Returns the model version string (e.g. 'tomato_vision_v1.0')."""
        pass

    @abstractmethod
    def get_supported_classes(self) -> List[str]:
        """Returns list of supported pathological classes."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Returns comprehensive model metadata (architecture, params, status)."""
        pass

    @abstractmethod
    def predict(self, image_bytes: bytes, top_k: int = 3) -> VisionPrediction:
        """
        Executes calibrated inference on raw image bytes.
        Returns normalized VisionPrediction with top-k candidates and uncertainty metrics.
        """
        pass


class CropVisionModelProvider(VisionModelProvider):
    """
    Generic, production-grade PyTorch MobileNetV3-Small provider for any crop.
    Loads weights, class mappings, preprocessing, and temperature scaling from models/vision/<crop>/
    """
    def __init__(self, crop_name: str, model_dir: Optional[str] = None):
        self.crop_name = crop_name.lower().strip()
        from app.core.config import settings
        candidates = [
            model_dir,
            os.path.join(settings.MODELS_DIR, "vision", self.crop_name),
            os.path.join("models", "vision", self.crop_name),
            os.path.join("..", "models", "vision", self.crop_name),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "models", "vision", self.crop_name)),
        ]
        resolved = None
        for c in candidates:
            if c and os.path.exists(os.path.join(c, "best_model.pth")):
                resolved = c
                break
        self.model_dir = resolved or model_dir or os.path.join("models", "vision", self.crop_name)
        self.model: Optional[torch.nn.Module] = None
        self.labels: Dict[int, str] = {}
        self.disease_keys: Dict[str, str] = {}
        self.common_names: Dict[str, str] = {}
        self.temperature: float = 1.0
        self.model_version: str = f"{self.crop_name}_vision_v1.0"
        self.status: str = "RESEARCH"
        self.is_loaded: bool = False
        self.metadata: Dict[str, Any] = {}

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        self._load_artifacts()

    def get_crop_name(self) -> str:
        return self.crop_name

    def get_model_version(self) -> str:
        return self.model_version

    def get_supported_classes(self) -> List[str]:
        return list(self.labels.values())

    def get_metadata(self) -> Dict[str, Any]:
        return self.metadata

    def _load_artifacts(self):
        try:
            labels_path = os.path.join(self.model_dir, "labels.json")
            weights_path = os.path.join(self.model_dir, "best_model.pth")
            calib_path = os.path.join(self.model_dir, "calibration.json")
            meta_path = os.path.join(self.model_dir, "metadata.json")

            if os.path.exists(labels_path):
                with open(labels_path, "r") as f:
                    raw_labels = json.load(f)
                    self.labels = {int(k): v for k, v in raw_labels.items()}
            else:
                self.labels = {0: f"{self.crop_name}___healthy"}

            if os.path.exists(calib_path):
                with open(calib_path, "r") as f:
                    calib_data = json.load(f)
                    self.temperature = float(calib_data.get("temperature", 1.0))

            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    self.metadata = json.load(f)
                    self.model_version = self.metadata.get("model_version", f"{self.crop_name}_vision_v1.0")
                    self.status = self.metadata.get("status", "CANDIDATE")

            # Instantiate architecture
            model = models.mobilenet_v3_small(weights=None)
            in_features = model.classifier[3].in_features
            model.classifier[3] = torch.nn.Linear(in_features, len(self.labels))

            if os.path.exists(weights_path):
                state_dict = torch.load(weights_path, map_location=torch.device("cpu"))
                model.load_state_dict(state_dict)
                logger.info("Loaded %s MobileNetV3 weights from %s", self.crop_name, weights_path)
            else:
                logger.warning("Model weights for %s not found at %s. Initialized untrained architecture.", self.crop_name, weights_path)

            model.eval()
            self.model = model
            self.is_loaded = True

        except Exception as e:
            logger.error("Failed to load CropVisionModelProvider for %s: %s", self.crop_name, str(e))
            self.is_loaded = False

    def predict(self, image_bytes: bytes, top_k: int = 3) -> VisionPrediction:
        # 1. Image Quality Gate
        gate_res: ImageQualityGateResult = ImageQualityGate.validate(image_bytes)
        if not gate_res.is_valid:
            return VisionPrediction(
                crop=self.crop_name,
                disease="QUALITY_CHECK_FAILED",
                common_name="Image Quality Verification Failed",
                confidence=0.0,
                calibrated_confidence=0.0,
                model_version=self.model_version,
                top_predictions=[],
                quality_status="FAILED",
                uncertainty_status="REJECTED",
                is_ood=True,
                inference_time_ms=0.0,
                quality_metrics=gate_res.metrics,
                is_reliable=False
            )

        t_start = time.perf_counter()

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img_rgb = img.convert("RGB")
                tensor = self.transform(img_rgb).unsqueeze(0)

            with torch.no_grad():
                logits = self.model(tensor)
                raw_probs = torch.softmax(logits, dim=1).squeeze(0)
                calib_logits = logits / max(self.temperature, 0.01)
                calib_probs = torch.softmax(calib_logits, dim=1).squeeze(0)

            k = min(top_k, len(self.labels))
            top_raw_vals, top_indices = torch.topk(raw_probs, k)
            top_calib_vals = calib_probs[top_indices]

            top_predictions: List[VisionTopPrediction] = []
            for i in range(k):
                c_idx = int(top_indices[i].item())
                c_name = self.labels.get(c_idx, "Unknown")
                reg_key = c_name.lower().replace(f"{self.crop_name}___", "").replace(" ", "_")
                com_name = c_name.replace("___", " - ").replace("_", " ")
                top_predictions.append(
                    VisionTopPrediction(
                        class_id=c_idx,
                        class_name=c_name,
                        disease_key=reg_key,
                        common_name=com_name,
                        confidence=round(float(top_raw_vals[i].item()), 4),
                        calibrated_confidence=round(float(top_calib_vals[i].item()), 4)
                    )
                )

            top_pred = top_predictions[0]
            inf_ms = round((time.perf_counter() - t_start) * 1000, 2)

            # 2. OOD & Uncertainty Validation
            ood_eval = VisionPredictionValidator.evaluate(
                top_confidence=top_pred.calibrated_confidence,
                crop_detected=self.crop_name,
                disease_predicted=top_pred.disease_key
            )

            is_reliable = ood_eval.is_in_distribution and (top_pred.calibrated_confidence >= VisionPredictionValidator.MIN_CONFIDENCE_THRESHOLD)

            return VisionPrediction(
                crop=self.crop_name,
                disease=top_pred.class_name,
                common_name=top_pred.common_name,
                confidence=top_pred.confidence,
                calibrated_confidence=top_pred.calibrated_confidence,
                model_version=self.model_version,
                top_predictions=top_predictions,
                quality_status="PASSED",
                uncertainty_status=ood_eval.uncertainty_level,
                is_ood=not ood_eval.is_in_distribution,
                inference_time_ms=inf_ms,
                quality_metrics=gate_res.metrics,
                is_reliable=is_reliable
            )

        except Exception as e:
            logger.error("CropVisionModelProvider inference failed for %s: %s", self.crop_name, str(e))
            inf_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return VisionPrediction(
                crop=self.crop_name,
                disease="INFERENCE_FAILED",
                common_name="Diagnosis Service Error",
                confidence=0.0,
                calibrated_confidence=0.0,
                model_version=self.model_version,
                top_predictions=[],
                quality_status="FAILED",
                uncertainty_status="UNRELIABLE",
                is_ood=True,
                inference_time_ms=inf_ms,
                quality_metrics=gate_res.metrics,
                is_reliable=False
            )


class TomatoVisionModelProvider(VisionModelProvider):
    """
    Adapter for the reference Tomato model trained in Phase 4 Step 6A.
    """
    def __init__(self):
        from app.services.vision.tomato_model import TomatoVisionModel
        self.inner_model = TomatoVisionModel.get_instance()

    def get_crop_name(self) -> str:
        return "tomato"

    def get_model_version(self) -> str:
        return self.inner_model.model_version

    def get_supported_classes(self) -> List[str]:
        return list(self.inner_model.labels.values())

    def get_metadata(self) -> Dict[str, Any]:
        meta_path = os.path.join("models", "vision", "tomato", "metadata.json")
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                return json.load(f)
        return {"model_name": "tomato_mobilenet_v3_small", "status": "VALIDATED"}

    def predict(self, image_bytes: bytes, top_k: int = 3) -> VisionPrediction:
        return self.inner_model.predict(image_bytes=image_bytes, top_k=top_k)
