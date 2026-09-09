import os
import io
import time
import json
import logging
import numpy as np
import torch
from PIL import Image
from typing import Dict, Any, List

import onnxruntime as ort

from app.schemas.vision import VisionPrediction, VisionTopPrediction
from app.services.vision.provider_contract import VisionModelProvider
from app.services.vision.quality_gate import ImageQualityGate, ImageQualityGateResult
from app.services.vision.validator import VisionPredictionValidator

logger = logging.getLogger(__name__)

class ONNXVisionModelProvider(VisionModelProvider):
    """
    Edge-compatible vision provider executing MobileNetV3 inference via ONNX Runtime.
    Maintains 100% equivalence with PyTorch provider pipeline:
    ImageQualityGate -> Preprocessing -> ONNX Runtime -> Temperature Calibration -> OOD Gate.
    """

    def __init__(self, crop_name: str, model_path: str, labels_path: str, calib_path: str = None):
        self.crop_name = crop_name.lower().strip()
        self.model_path = model_path
        self.labels_path = labels_path
        self.model_version = f"{self.crop_name}_edge_onnx_v1.0"
        self.temperature = 1.0

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"ONNX model not found at {model_path}")
        if not os.path.exists(labels_path):
            raise FileNotFoundError(f"Labels file not found at {labels_path}")

        with open(labels_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "classes" in data and isinstance(data["classes"], list):
                self.classes = data["classes"]
            elif isinstance(data, dict):
                try:
                    self.classes = [data[str(i)] for i in range(len(data))]
                except KeyError:
                    self.classes = list(data.values())
            elif isinstance(data, list):
                self.classes = data
            else:
                self.classes = []

        if calib_path and os.path.exists(calib_path):
            try:
                with open(calib_path, "r", encoding="utf-8") as f:
                    cal = json.load(f)
                    self.temperature = float(cal.get("temperature", 1.0))
            except Exception:
                pass

        # Initialize ONNX Runtime Inference Session
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.input_type = self.session.get_inputs()[0].type
        self.is_fp16 = "float16" in self.input_type

    def get_crop_name(self) -> str:
        return self.crop_name

    def get_model_version(self) -> str:
        return self.model_version

    def get_supported_classes(self) -> List[str]:
        return self.classes

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "crop": self.crop_name,
            "model_version": self.model_version,
            "runtime": "onnxruntime",
            "model_path": self.model_path,
            "classes": self.classes,
            "temperature": self.temperature,
            "is_fp16": self.is_fp16,
            "architecture": "MobileNetV3-Small"
        }

    def preprocess_image(self, image_bytes: bytes) -> np.ndarray:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img_rgb = img.convert("RGB").resize((224, 224), Image.Resampling.BILINEAR)
            arr = np.array(img_rgb, dtype=np.float32) / 255.0
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            arr = (arr - mean) / std
            arr = np.transpose(arr, (2, 0, 1))
            tensor = np.expand_dims(arr, axis=0)
            if self.is_fp16:
                tensor = tensor.astype(np.float16)
            return tensor

    def predict(self, image_bytes: bytes, top_k: int = 3) -> VisionPrediction:
        # Step 1: Image Quality Gate
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
            input_tensor = self.preprocess_image(image_bytes)

            # ONNX Runtime Inference
            raw_out = self.session.run(None, {self.input_name: input_tensor})[0][0]
            logits = torch.from_numpy(raw_out.astype(np.float32))

            # Temperature Scaling
            calibrated_logits = logits / self.temperature
            raw_probs = torch.softmax(logits, dim=0)
            calibrated_probs = torch.softmax(calibrated_logits, dim=0)

            top_probs, top_indices = torch.topk(calibrated_probs, min(top_k, len(self.classes)))

            top_predictions: List[VisionTopPrediction] = []
            for i in range(min(top_k, len(self.classes))):
                c_idx = int(top_indices[i].item())
                c_name = self.classes[c_idx]
                reg_key = c_name.lower().replace(f"{self.crop_name}___", "").replace(" ", "_")
                com_name = c_name.replace("___", " - ").replace("_", " ")
                top_predictions.append(
                    VisionTopPrediction(
                        class_id=c_idx,
                        class_name=c_name,
                        disease_key=reg_key,
                        common_name=com_name,
                        confidence=round(float(raw_probs[c_idx].item()), 4),
                        calibrated_confidence=round(float(top_probs[i].item()), 4)
                    )
                )

            top_pred = top_predictions[0]
            inference_time_ms = round((time.perf_counter() - t_start) * 1000, 2)

            # OOD & Uncertainty Validation
            val_res = VisionPredictionValidator.evaluate(
                top_confidence=top_pred.calibrated_confidence,
                crop_detected=self.crop_name,
                disease_predicted=top_pred.disease_key
            )

            return VisionPrediction(
                crop=self.crop_name,
                disease=top_pred.class_name,
                common_name=top_pred.common_name,
                confidence=top_pred.confidence,
                calibrated_confidence=top_pred.calibrated_confidence,
                model_version=self.model_version,
                top_predictions=top_predictions,
                quality_status="PASSED",
                uncertainty_status=val_res.uncertainty_level,
                is_ood=not val_res.is_in_distribution,
                inference_time_ms=inference_time_ms,
                quality_metrics=gate_res.metrics,
                is_reliable=(val_res.is_in_distribution and val_res.uncertainty_level == "LOW")
            )

        except Exception as e:
            logger.error("ONNX Edge inference failure for %s: %s", self.crop_name, str(e))
            return VisionPrediction(
                crop=self.crop_name,
                disease="ERROR_DIAGNOSIS_FAILED",
                common_name="Diagnosis Failed",
                confidence=0.0,
                calibrated_confidence=0.0,
                model_version=self.model_version,
                top_predictions=[],
                quality_status="ERROR",
                uncertainty_status="UNRELIABLE",
                is_ood=True,
                inference_time_ms=0.0,
                quality_metrics={},
                is_reliable=False
            )
