import os
import json
from typing import Dict, Any, List, Optional
from app.services.vision.field_validation.schemas import CropFieldEvaluationSummary

BENCHMARK_METRICS = {
    "tomato": {"accuracy": 0.9350, "macro_f1": 0.9356, "status": "VALIDATED"},
    "banana": {"accuracy": 0.9238, "macro_f1": 0.9256, "status": "VALIDATED"},
    "guava": {"accuracy": 0.9200, "macro_f1": 0.9169, "status": "VALIDATED"},
    "corn_maize": {"accuracy": 0.8900, "macro_f1": 0.8893, "status": "VALIDATED"},
    "apple": {"accuracy": 0.8300, "macro_f1": 0.8256, "status": "CANDIDATE"},
    "chilli": {"accuracy": 0.7800, "macro_f1": 0.7848, "status": "CANDIDATE"},
    "cucumber_pumpkin": {"accuracy": 0.7440, "macro_f1": 0.7520, "status": "CANDIDATE"},
    "sugarcane": {"accuracy": 0.7300, "macro_f1": 0.7296, "status": "CANDIDATE"},
    "potato": {"accuracy": 0.6889, "macro_f1": 0.6675, "status": "CANDIDATE"},
    "rice": {"accuracy": 0.3650, "macro_f1": 0.3522, "status": "RESEARCH_ONLY"}
}

class DomainShiftAnalyzer:
    """
    Computes domain degradation deltas between laboratory/curated benchmarks and real on-farm smartphone images.
    """

    @classmethod
    def get_benchmark_baseline(cls, crop: str) -> Dict[str, Any]:
        canonical = crop.lower().strip()
        # First attempt to read live from models/vision/<crop>/metadata.json and metrics.json
        meta_path = os.path.join("models", "vision", canonical, "metadata.json")
        metrics_path = os.path.join("models", "vision", canonical, "metrics.json")
        status = "CANDIDATE"
        acc, f1 = 0.0, 0.0

        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    data = json.load(f)
                    status = data.get("status", "CANDIDATE")
                    acc = float(data.get("accuracy", 0.0))
                    f1 = float(data.get("macro_f1", 0.0))
            except Exception:
                pass

        if acc == 0.0 and os.path.exists(metrics_path):
            try:
                with open(metrics_path, "r") as f:
                    m_data = json.load(f)
                    acc = float(m_data.get("accuracy", 0.0))
                    f1 = float(m_data.get("macro_f1", 0.0))
            except Exception:
                pass

        if acc == 0.0 and canonical in BENCHMARK_METRICS:
            return BENCHMARK_METRICS[canonical]

        return {
            "accuracy": round(acc, 4),
            "macro_f1": round(f1, 4),
            "status": status
        }

    @classmethod
    def compute_shift(cls, crop_summary: CropFieldEvaluationSummary) -> Dict[str, Any]:
        baseline = cls.get_benchmark_baseline(crop_summary.crop)
        bench_acc = baseline["accuracy"]
        bench_f1 = baseline["macro_f1"]

        field_acc = crop_summary.accuracy
        field_f1 = crop_summary.macro_f1

        delta_acc = round(field_acc - bench_acc, 4)
        delta_f1 = round(field_f1 - bench_f1, 4)

        has_data = crop_summary.total_images > 0

        return {
            "crop": crop_summary.crop,
            "has_field_data": has_data,
            "benchmark_accuracy": bench_acc,
            "field_accuracy": field_acc if has_data else None,
            "delta_accuracy": delta_acc if has_data else None,
            "benchmark_macro_f1": bench_f1,
            "field_macro_f1": field_f1 if has_data else None,
            "delta_macro_f1": delta_f1 if has_data else None,
            "quality_gate_passed": crop_summary.quality_gate_passed,
            "quality_gate_rejected": crop_summary.quality_gate_rejected,
            "abstention_rate": crop_summary.abstention_rate,
            "ood_rejection_rate": crop_summary.ood_rejection_rate
        }
