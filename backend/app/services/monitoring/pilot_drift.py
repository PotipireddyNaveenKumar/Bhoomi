from typing import Dict, Any, List, Optional
import math


class PilotDriftDetector:
    """
    Deterministic drift detection for Vision, Voice, and Task behavior in field pilots.
    Adheres strictly to the statistical minimum sample size rule:
    Does NOT declare statistically significant drift without N >= 30 samples.
    """

    MIN_SAMPLES_FOR_DRIFT = 30

    @classmethod
    def detect_vision_drift(
        cls,
        benchmark_stats: Dict[str, Any],
        field_stats: Dict[str, Any],
        min_samples: int = 30
    ) -> Dict[str, Any]:
        """
        Compares controlled benchmark metrics against real field metrics.
        Computes confidence shift, accuracy shift, and Macro-F1 shift.
        """
        n_field = field_stats.get("evaluated_images", field_stats.get("total_samples", 0))

        if n_field < min_samples:
            return {
                "drift_detected": False,
                "status": "INSUFFICIENT_SAMPLE_SIZE",
                "sample_size": n_field,
                "min_required": min_samples,
                "message": (
                    f"Sample size too small ({n_field} samples < {min_samples} required). "
                    "Cannot compute statistically valid vision drift."
                )
            }

        bench_acc = float(benchmark_stats.get("accuracy", 0.0))
        bench_f1 = float(benchmark_stats.get("macro_f1", 0.0))
        bench_conf = float(benchmark_stats.get("mean_confidence", 0.85))

        field_acc = float(field_stats.get("accuracy", 0.0))
        field_f1 = float(field_stats.get("macro_f1", 0.0))
        field_conf = float(field_stats.get("mean_confidence", 0.0))

        acc_shift = round(field_acc - bench_acc, 4)
        f1_shift = round(field_f1 - bench_f1, 4)
        conf_shift = round(field_conf - bench_conf, 4)

        # Flag drift if accuracy or F1 drops by more than 15 percentage points
        has_significant_degradation = acc_shift < -0.15 or f1_shift < -0.15

        return {
            "drift_detected": has_significant_degradation,
            "status": "DRIFT_DETECTED" if has_significant_degradation else "NO_DRIFT",
            "sample_size": n_field,
            "shifts": {
                "accuracy_shift": acc_shift,
                "macro_f1_shift": f1_shift,
                "confidence_shift": conf_shift
            },
            "interpretation": (
                "Significant domain shift observed from benchmark to field."
                if has_significant_degradation else
                "Field distribution is within tolerable variance of benchmark."
            )
        }

    @classmethod
    def detect_voice_drift(
        cls,
        baseline_stats: Dict[str, Any],
        current_stats: Dict[str, Any],
        min_samples: int = 30
    ) -> Dict[str, Any]:
        """
        Detects drift in voice intent accuracy, STT confidence, or language distribution.
        """
        n_current = current_stats.get("total_samples", 0)
        if n_current < min_samples:
            return {
                "drift_detected": False,
                "status": "INSUFFICIENT_SAMPLE_SIZE",
                "sample_size": n_current,
                "min_required": min_samples,
                "message": f"Sample size ({n_current}) below threshold ({min_samples}). Voice drift withheld."
            }

        base_intent_acc = float(baseline_stats.get("intent_accuracy", 0.90))
        curr_intent_acc = float(current_stats.get("intent_accuracy", 0.0))
        intent_shift = round(curr_intent_acc - base_intent_acc, 4)

        base_defect_rate = float(baseline_stats.get("critical_defect_rate", 0.01))
        curr_defect_rate = float(current_stats.get("critical_defect_rate", 0.0))
        defect_jump = round(curr_defect_rate - base_defect_rate, 4)

        drift = (intent_shift < -0.10) or (defect_jump > 0.05)

        return {
            "drift_detected": drift,
            "status": "DRIFT_DETECTED" if drift else "NO_DRIFT",
            "sample_size": n_current,
            "shifts": {
                "intent_accuracy_shift": intent_shift,
                "defect_rate_jump": defect_jump
            }
        }

    @classmethod
    def detect_task_drift(
        cls,
        baseline_stats: Dict[str, Any],
        current_stats: Dict[str, Any],
        min_samples: int = 30
    ) -> Dict[str, Any]:
        """
        Detects longitudinal drift in farmer task completion delay or postponement behavior.
        """
        n_current = current_stats.get("total_records", 0)
        if n_current < min_samples:
            return {
                "drift_detected": False,
                "status": "INSUFFICIENT_SAMPLE_SIZE",
                "sample_size": n_current,
                "min_required": min_samples,
                "message": f"Sample size ({n_current}) below threshold ({min_samples}). Task drift withheld."
            }

        base_delay = float(baseline_stats.get("median_completion_delay_days", 1.0))
        curr_delay = float(current_stats.get("median_completion_delay_days", 0.0))
        delay_shift = round(curr_delay - base_delay, 2)

        base_postpone = float(baseline_stats.get("postponement_rate", 0.15))
        curr_postpone = float(current_stats.get("postponement_rate", 0.0))
        postpone_shift = round(curr_postpone - base_postpone, 4)

        drift = (delay_shift > 3.0) or (postpone_shift > 0.20)

        return {
            "drift_detected": drift,
            "status": "DRIFT_DETECTED" if drift else "NO_DRIFT",
            "sample_size": n_current,
            "shifts": {
                "delay_shift_days": delay_shift,
                "postponement_shift": postpone_shift
            }
        }
