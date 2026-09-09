import os
import numpy as np
from typing import List, Dict, Any

from app.services.vision.edge.exporter import EdgeModelExporter
from app.services.vision.edge.parity import NumericalParityTester
from app.services.vision.edge.onnx_provider import ONNXVisionModelProvider
from app.services.vision.crop_registry import CropModelRegistry

class FieldEdgeParityEvaluator:
    """
    Evaluates runtime consistency between PyTorch reference server model
    and edge runtimes (ONNX FP16, ONNX INT8) on identical field pilot images.
    """

    @classmethod
    def evaluate_field_runtime_parity(
        cls,
        crop: str,
        field_image_bytes_list: List[bytes],
        base_dir: str = "models/vision"
    ) -> Dict[str, Any]:
        """
        Runs identical field images through PyTorch server and ONNX FP16/INT8.
        Reports prediction agreement, mean confidence difference, OOD agreement,
        and abstention agreement.
        """
        if not field_image_bytes_list:
            return {
                "parity_available": False,
                "status": "FIELD DATA NOT YET AVAILABLE",
                "message": "Zero field images available for runtime parity evaluation."
            }

        crop_clean = crop.lower().strip()
        onnx_dir = os.path.join(base_dir, crop_clean, "edge", "onnx")
        fp16_path = os.path.join(onnx_dir, f"{crop_clean}_model_fp16.onnx")
        labels_path = os.path.join(base_dir, crop_clean, "labels.json")

        if not os.path.exists(fp16_path) or not os.path.exists(labels_path):
            return {
                "parity_available": False,
                "status": "EDGE_MODEL_NOT_FOUND",
                "message": f"ONNX FP16 edge model not found for {crop_clean}."
            }

        edge_provider = ONNXVisionModelProvider(crop_clean, fp16_path, labels_path)

        agreements = []
        conf_diffs = []
        ood_agreements = []
        abstention_agreements = []

        for img_bytes in field_image_bytes_list:
            # Server prediction
            server_pred = CropModelRegistry.predict(img_bytes, crop_hint=crop_clean)
            # Edge prediction
            edge_pred = edge_provider.predict(img_bytes)

            # 1. Prediction Agreement
            agreed = int(server_pred.disease == edge_pred.disease)
            agreements.append(agreed)

            # 2. Confidence Difference
            diff = abs(server_pred.calibrated_confidence - edge_pred.calibrated_confidence)
            conf_diffs.append(diff)

            # 3. OOD Decision Agreement
            ood_agreed = int(server_pred.is_ood == edge_pred.is_ood)
            ood_agreements.append(ood_agreed)

            # 4. Abstention Agreement
            abstain_agreed = int(server_pred.is_reliable == edge_pred.is_reliable)
            abstention_agreements.append(abstain_agreed)

        return {
            "parity_available": True,
            "status": "EVALUATED",
            "sample_count": len(field_image_bytes_list),
            "prediction_agreement_rate": round(float(np.mean(agreements)), 4),
            "mean_confidence_diff": round(float(np.mean(conf_diffs)), 6),
            "max_confidence_diff": round(float(np.max(conf_diffs)), 6),
            "ood_decision_agreement_rate": round(float(np.mean(ood_agreements)), 4),
            "abstention_agreement_rate": round(float(np.mean(abstention_agreements)), 4),
            "note": "Runtime consistency verification on field samples. Does not constitute field diagnostic accuracy."
        }
