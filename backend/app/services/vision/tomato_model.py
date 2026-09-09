import os
import io
import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

import torch
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image

from app.schemas.vision import VisionPrediction, VisionTopPrediction
from app.services.vision.validator import VisionPredictionValidator
from app.services.vision.quality_gate import ImageQualityGate, ImageQualityGateResult

logger = logging.getLogger(__name__)

# Canonical map from PlantVillage labels to registry disease keys
PLANTVILLAGE_TO_REGISTRY_KEY = {
    "Tomato___Bacterial_spot": "bacterial_spot",
    "Tomato___Early_blight": "early_blight",
    "Tomato___Late_blight": "late_blight",
    "Tomato___Leaf_Mold": "leaf_mold",
    "Tomato___Septoria_leaf_spot": "septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite": "spider_mites",
    "Tomato___Target_Spot": "target_spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "yellow_leaf_curl_virus",
    "Tomato___Tomato_mosaic_virus": "mosaic_virus",
    "Tomato___healthy": "healthy"
}

PLANTVILLAGE_COMMON_NAMES = {
    "Tomato___Bacterial_spot": "Bacterial Spot",
    "Tomato___Early_blight": "Early Blight",
    "Tomato___Late_blight": "Late Blight",
    "Tomato___Leaf_Mold": "Leaf Mold",
    "Tomato___Septoria_leaf_spot": "Septoria Leaf Spot",
    "Tomato___Spider_mites Two-spotted_spider_mite": "Two-Spotted Spider Mites",
    "Tomato___Target_Spot": "Target Spot",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Tomato Yellow Leaf Curl Virus (TYLCV)",
    "Tomato___Tomato_mosaic_virus": "Tomato Mosaic Virus (ToMV)",
    "Tomato___healthy": "Healthy Tomato Leaf"
}

class TomatoVisionModel:
    """
    Production Deep Learning Classifier for Tomato Foliar Pathology.
    Architecture: MobileNetV3-Small with Temperature-Scaled Confidence Calibration.
    Supports 10 standard pathological classes.
    """
    _instance: Optional["TomatoVisionModel"] = None

    def __init__(self, model_dir: Optional[str] = None):
        from app.core.config import settings
        candidates = [
            model_dir,
            os.path.join(settings.MODELS_DIR, "vision", "tomato"),
            "models/vision/tomato",
            "../models/vision/tomato",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "models", "vision", "tomato")),
        ]
        resolved = None
        for c in candidates:
            if c and os.path.exists(os.path.join(c, "best_model.pth")):
                resolved = c
                break
        self.model_dir = resolved or model_dir or "models/vision/tomato"
        self.model: Optional[torch.nn.Module] = None
        self.labels: Dict[int, str] = {}
        self.temperature: float = 1.0
        self.model_version: str = "tomato_vision_v1.0"
        self.is_loaded: bool = False

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        self._load_artifacts()

    @classmethod
    def get_instance(cls, model_dir: str = "models/vision/tomato") -> "TomatoVisionModel":
        if cls._instance is None:
            cls._instance = TomatoVisionModel(model_dir=model_dir)
        return cls._instance

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
                self.labels = {i: k for i, k in enumerate(PLANTVILLAGE_TO_REGISTRY_KEY.keys())}

            if os.path.exists(calib_path):
                with open(calib_path, "r") as f:
                    calib_data = json.load(f)
                    self.temperature = float(calib_data.get("temperature", 1.0))

            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    meta_data = json.load(f)
                    self.model_version = meta_data.get("model_version", "tomato_vision_v1.0")

            # Instantiate architecture
            model = models.mobilenet_v3_small(weights=None)
            in_features = model.classifier[3].in_features
            model.classifier[3] = torch.nn.Linear(in_features, len(self.labels))

            if os.path.exists(weights_path):
                state_dict = torch.load(weights_path, map_location=torch.device("cpu"))
                model.load_state_dict(state_dict)
                logger.info("Loaded trained Tomato MobileNetV3-Small weights from %s", weights_path)
            else:
                logger.warning("Tomato model weights not found at %s. Initialized untrained architecture.", weights_path)

            model.eval()
            self.model = model
            self.is_loaded = True

        except Exception as e:
            logger.error("Failed to load TomatoVisionModel: %s", str(e))
            self.is_loaded = False

    def predict(self, image_bytes: bytes, top_k: int = 3) -> VisionPrediction:
        """
        Executes calibrated inference on raw image bytes.
        Returns normalized VisionPrediction with top-k candidates and uncertainty metrics.
        """
        # 1. Image Quality Gate
        gate_res: ImageQualityGateResult = ImageQualityGate.validate(image_bytes)
        if not gate_res.is_valid:
            return VisionPrediction(
                crop="tomato",
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

            # Extract top-k
            k = min(top_k, len(self.labels))
            top_raw_vals, top_indices = torch.topk(raw_probs, k)
            top_calib_vals = calib_probs[top_indices]

            top_predictions: List[VisionTopPrediction] = []
            for i in range(k):
                c_idx = int(top_indices[i].item())
                c_name = self.labels.get(c_idx, "Unknown")
                reg_key = PLANTVILLAGE_TO_REGISTRY_KEY.get(c_name, "leaf_curl")
                com_name = PLANTVILLAGE_COMMON_NAMES.get(c_name, c_name)
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
                crop_detected="tomato",
                disease_predicted=top_pred.disease_key
            )

            is_reliable = ood_eval.is_in_distribution and (top_pred.calibrated_confidence >= VisionPredictionValidator.MIN_CONFIDENCE_THRESHOLD)

            return VisionPrediction(
                crop="tomato",
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
            logger.error("TomatoVisionModel inference failed: %s", str(e))
            inf_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return VisionPrediction(
                crop="tomato",
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
