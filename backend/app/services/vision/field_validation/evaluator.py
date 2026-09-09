import os
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

from app.schemas.vision import VisionPrediction
from app.services.vision.crop_registry import CropModelRegistry
from app.services.vision.quality_gate import ImageQualityGate, ImageQualityGateResult
from app.services.vision.field_validation.schemas import (
    FieldImageMetadata,
    ExpertLabelRecord,
    AnnotationState
)

logger = logging.getLogger(__name__)

class FieldValidationEvaluator:
    """
    Executes strictly BLIND evaluation on field images.
    The underlying vision model receives ONLY raw image bytes and the crop identifier.
    Ground-truth labels and clinical metadata are isolated until inference is frozen.
    """

    @classmethod
    def evaluate_image_blind(
        cls,
        image_bytes: bytes,
        crop: str
    ) -> Tuple[VisionPrediction, ImageQualityGateResult]:
        """
        Blind inference execution:
        Passes only image_bytes and crop name into the defensive pipeline:
        1. ImageQualityGate
        2. CropModelRegistry -> MobileNetV3-Small
        3. Temperature Scaling
        4. VisionPredictionValidator (OOD / Uncertainty)
        """
        # Step 1: Quality Gate
        gate_res = ImageQualityGate.validate(image_bytes)

        # Step 2: Crop Model Inference
        pred = CropModelRegistry.predict(
            image_bytes=image_bytes,
            crop_hint=crop,
            top_k=3
        )

        return pred, gate_res

    @classmethod
    def evaluate_crop_field_dataset(
        cls,
        crop: str,
        image_records: List[Tuple[FieldImageMetadata, ExpertLabelRecord]],
        base_image_dir: str = "data/field_validation/images"
    ) -> List[Dict[str, Any]]:
        """
        Iterates through the field validation set for a crop,
        executing blind inference on each file and matching post-hoc with expert annotations.
        """
        results = []

        for meta, expert in image_records:
            img_full_path = meta.image_path
            if not os.path.isabs(img_full_path):
                # Try relative to base_image_dir or SIH workspace
                candidate_paths = [
                    img_full_path,
                    os.path.join(base_image_dir, meta.crop, os.path.basename(img_full_path)),
                    os.path.join("data", "field_validation", img_full_path)
                ]
                for cp in candidate_paths:
                    if os.path.exists(cp):
                        img_full_path = cp
                        break

            if not os.path.exists(img_full_path):
                logger.warning("Field image %s not found on disk at %s", meta.image_id, img_full_path)
                continue

            with open(img_full_path, "rb") as f:
                img_bytes = f.read()

            # BLIND EVALUATION: Only img_bytes and crop hint passed
            pred, gate_res = cls.evaluate_image_blind(image_bytes=img_bytes, crop=crop)

            # Match post-hoc with expert label
            pred_disease_normalized = pred.disease.lower().replace(f"{crop}___", "").replace(" ", "_")
            expert_disease_normalized = expert.expert_label.lower().replace(f"{crop}___", "").replace(" ", "_")

            is_correct = (
                pred.is_reliable and
                (pred_disease_normalized == expert_disease_normalized or
                 expert_disease_normalized in pred_disease_normalized or
                 pred_disease_normalized in expert_disease_normalized)
            )

            results.append({
                "image_id": meta.image_id,
                "crop": crop,
                "expert_label": expert.expert_label,
                "expert_normalized": expert_disease_normalized,
                "annotation_state": expert.annotation_state,
                "predicted_disease": pred.disease,
                "predicted_normalized": pred_disease_normalized,
                "confidence": pred.calibrated_confidence,
                "is_reliable": pred.is_reliable,
                "is_ood": pred.is_ood,
                "uncertainty_status": pred.uncertainty_status,
                "quality_gate_status": gate_res.is_valid,
                "quality_rejection_reason": gate_res.reason if not gate_res.is_valid else None,
                "inference_time_ms": pred.inference_time_ms,
                "is_correct": is_correct,
                "lighting_condition": meta.lighting_condition,
                "camera_device": meta.camera_device,
                "image_distance": meta.image_distance
            })

        return results
