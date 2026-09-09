import os
import json
import statistics
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Optional
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)
from app.services.vision.field_validation.schemas import (
    ConfidenceBucketMetrics,
    CropFieldEvaluationSummary,
    ModelFieldStatus,
    FieldFailureCase
)

class FieldMetricsCalculator:
    """
    Calculates primary (CONFIRMED), secondary (PROBABLE), defensive, calibration,
    high-confidence errors, and failure-mode categorizations for field evaluation runs.
    """

    CONFIDENCE_BUCKETS = [
        ("0.00-0.54", 0.0, 0.5499),
        ("0.55-0.69", 0.55, 0.6999),
        ("0.70-0.84", 0.70, 0.8499),
        ("0.85-1.00", 0.85, 1.00)
    ]

    @classmethod
    def calculate_confidence_buckets(
        cls,
        eval_results: List[Dict[str, Any]]
    ) -> List[ConfidenceBucketMetrics]:
        buckets = []
        for name, low, high in cls.CONFIDENCE_BUCKETS:
            in_bucket = [r for r in eval_results if low <= r["confidence"] <= high]
            count = len(in_bucket)
            correct = sum(1 for r in in_bucket if r["is_correct"])
            acc = round(correct / count, 4) if count > 0 else 0.0
            buckets.append(ConfidenceBucketMetrics(
                bucket_range=name,
                sample_count=count,
                correct_count=correct,
                accuracy=acc
            ))
        return buckets

    @classmethod
    def categorize_failures(
        cls,
        crop: str,
        eval_results: List[Dict[str, Any]],
        failure_dir: str = "data/field_validation/reports/failure_cases"
    ) -> Tuple[List[FieldFailureCase], int, int]:
        """
        Analyzes mispredictions, categorizes causes (lighting, blur, high-confidence error, etc.),
        and writes structured failure case records.
        """
        failure_cases: List[FieldFailureCase] = []
        high_conf_errors = 0
        low_conf_correct = 0

        for r in eval_results:
            is_correct = r.get("is_correct", False)
            conf = r.get("confidence", 0.0)

            if is_correct:
                if conf < 0.55:
                    low_conf_correct += 1
                continue

            # Incorrect prediction analysis
            if conf >= 0.70:
                category = "HIGH_CONFIDENCE_WRONG_PREDICTION"
                high_conf_errors += 1
            elif not r.get("quality_gate_status", True):
                q_reason = str(r.get("quality_rejection_reason", "")).upper()
                if "BLUR" in q_reason:
                    category = "BLUR_DEFECT"
                elif "DARK" in q_reason or "OVEREXPOSED" in q_reason:
                    category = "POOR_LIGHTING"
                else:
                    category = "IMAGE_QUALITY_DEFECT"
            elif r.get("lighting_condition") in ["shaded", "harsh_glare", "overcast", "flash_illuminated"]:
                category = "POOR_LIGHTING"
            elif r.get("image_distance") in ["whole_plant_canopy", "distant_bed"]:
                category = "BACKGROUND_INTERFERENCE"
            elif r.get("is_ood", False):
                category = "OOD_MISCLASSIFICATION"
            else:
                category = "VISUALLY_SIMILAR_DISEASE"

            detail = (
                f"Expected '{r.get('expert_label')}', predicted '{r.get('predicted_disease')}' "
                f"with {conf*100:.1f}% confidence ({category})."
            )

            fc = FieldFailureCase(
                image_id=r.get("image_id", "unknown"),
                crop=crop,
                expert_label=r.get("expert_label", "unknown"),
                predicted_disease=r.get("predicted_disease", "unknown"),
                confidence=conf,
                uncertainty_status=r.get("uncertainty_status", "UNKNOWN"),
                failure_category=category,
                details=detail
            )
            failure_cases.append(fc)

        # Save failure records if failures exist
        if failure_cases:
            try:
                os.makedirs(failure_dir, exist_ok=True)
                out_path = os.path.join(failure_dir, f"failures_{crop}.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump([fc.model_dump() for fc in failure_cases], f, indent=2)
            except Exception:
                pass

        return failure_cases, high_conf_errors, low_conf_correct

    @classmethod
    def calculate_crop_metrics(
        cls,
        crop: str,
        eval_results: List[Dict[str, Any]],
        benchmark_accuracy: float = 0.0,
        benchmark_macro_f1: float = 0.0
    ) -> CropFieldEvaluationSummary:
        total = len(eval_results)
        if total == 0:
            return CropFieldEvaluationSummary(
                crop=crop,
                total_images=0,
                evaluated_images=0,
                quality_gate_passed=0,
                quality_gate_rejected=0,
                rejection_reasons={},
                accuracy=0.0,
                macro_precision=0.0,
                macro_recall=0.0,
                macro_f1=0.0,
                weighted_f1=0.0,
                abstention_rate=0.0,
                ood_rejection_rate=0.0,
                low_confidence_rate=0.0,
                mean_confidence=0.0,
                median_confidence=0.0,
                confidence_buckets=[],
                confusion_matrix=[],
                per_class_metrics={},
                benchmark_accuracy=benchmark_accuracy,
                benchmark_macro_f1=benchmark_macro_f1,
                delta_accuracy=0.0,
                delta_macro_f1=0.0,
                current_status=ModelFieldStatus.RESEARCH_ONLY if crop.lower() == "rice" else ModelFieldStatus.FIELD_PENDING,
                field_validation_statement="Rice model designated RESEARCH_ONLY due to morphological lesion ambiguity." if crop.lower() == "rice" else "FIELD DATA NOT YET AVAILABLE",
                high_confidence_error_count=0,
                low_confidence_correct_count=0,
                probable_accuracy=None,
                probable_macro_f1=None,
                failure_cases=[]
            )

        # Quality Gate filtering
        q_passed = [r for r in eval_results if r["quality_gate_status"]]
        q_rejected = [r for r in eval_results if not r["quality_gate_status"]]
        
        reasons = defaultdict(int)
        for r in q_rejected:
            reason = r.get("quality_rejection_reason") or "UNSPECIFIED"
            reasons[reason] += 1

        # Defensive rates
        abstentions = sum(1 for r in eval_results if not r.get("is_reliable", True))
        oods = sum(1 for r in eval_results if r.get("is_ood", False))
        low_confs = sum(1 for r in eval_results if r.get("confidence", 0.0) < 0.55)

        abstention_rate = round(abstentions / total, 4)
        ood_rate = round(oods / total, 4)
        low_conf_rate = round(low_confs / total, 4)

        confidences = [r.get("confidence", 0.0) for r in eval_results]
        mean_conf = round(statistics.mean(confidences), 4) if confidences else 0.0
        median_conf = round(statistics.median(confidences), 4) if confidences else 0.0

        buckets = cls.calculate_confidence_buckets(eval_results)
        failure_cases, high_conf_errs, low_conf_corr = cls.categorize_failures(crop, eval_results)

        # Primary Metrics (Evaluated ONLY on CONFIRMED expert labels)
        confirmed_evaluable = [r for r in q_passed if r.get("annotation_state") == "CONFIRMED"]
        if confirmed_evaluable:
            y_true = [r.get("expert_normalized") or r.get("expert_label") for r in confirmed_evaluable]
            y_pred = [r.get("predicted_normalized") or r.get("predicted_disease") for r in confirmed_evaluable]

            labels = sorted(list(set(y_true + y_pred)))
            acc = round(accuracy_score(y_true, y_pred), 4)
            macro_p = round(precision_score(y_true, y_pred, average="macro", zero_division=0), 4)
            macro_r = round(recall_score(y_true, y_pred, average="macro", zero_division=0), 4)
            macro_f = round(f1_score(y_true, y_pred, average="macro", zero_division=0), 4)
            weight_f = round(f1_score(y_true, y_pred, average="weighted", zero_division=0), 4)

            rep = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
            cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()
        else:
            acc = macro_p = macro_r = macro_f = weight_f = 0.0
            rep = {}
            cm = []

        # Secondary Metrics (PROBABLE labels reported separately)
        probable_evaluable = [r for r in q_passed if r.get("annotation_state") == "PROBABLE"]
        prob_acc = None
        prob_f1 = None
        if probable_evaluable:
            p_true = [r["expert_normalized"] for r in probable_evaluable]
            p_pred = [r["predicted_normalized"] for r in probable_evaluable]
            prob_acc = round(accuracy_score(p_true, p_pred), 4)
            prob_f1 = round(f1_score(p_true, p_pred, average="macro", zero_division=0), 4)

        delta_acc = round(acc - benchmark_accuracy, 4)
        delta_f1 = round(macro_f - benchmark_macro_f1, 4)

        # Lifecycle Status Determination
        if crop == "rice":
            status = ModelFieldStatus.RESEARCH_ONLY
            statement = "Rice model designated RESEARCH_ONLY due to morphological ambiguity."
        elif total < 30:
            status = ModelFieldStatus.FIELD_PENDING
            statement = f"Field validation active ({total} images); pilot minimum target (30 images) not yet met."
        elif macro_f >= 0.80 and delta_f1 >= -0.15 and high_conf_errs == 0:
            status = ModelFieldStatus.FIELD_VALIDATED
            statement = "Field evaluation requirements satisfied with zero high-confidence errors."
        elif macro_f < 0.65 or delta_f1 < -0.30 or high_conf_errs > 3:
            status = ModelFieldStatus.FIELD_UNSAFE
            statement = "Severe in-field domain degradation or high-confidence failures detected; field diagnosis blocked."
        else:
            status = ModelFieldStatus.FIELD_LIMITED
            statement = "Acceptable field performance under confidence gating; full validation pending further diversity."

        # Diversity and Multi-Disease Tracking
        farms = set(r.get("farm_id_hash") or r.get("farmer_id_hash") for r in eval_results if r.get("farm_id_hash") or r.get("farmer_id_hash"))
        plants = set(r.get("plant_id_hash") for r in eval_results if r.get("plant_id_hash"))
        sessions = set(r.get("collection_session_id") for r in eval_results if r.get("collection_session_id"))
        devices = set(r.get("camera_device") or r.get("device_model") for r in eval_results if r.get("camera_device") or r.get("device_model"))
        multi_disease_count = sum(1 for r in eval_results if r.get("is_multi_label") or r.get("disease_condition_type") == "multiple" or bool(r.get("secondary_diseases")))

        from app.services.vision.field_validation.group_evaluator import FarmSessionGroupManager
        group_metrics = FarmSessionGroupManager.aggregate_group_predictions(eval_results)

        return CropFieldEvaluationSummary(
            crop=crop,
            total_images=total,
            evaluated_images=len(confirmed_evaluable),
            quality_gate_passed=len(q_passed),
            quality_gate_rejected=len(q_rejected),
            rejection_reasons=dict(reasons),
            accuracy=acc,
            macro_precision=macro_p,
            macro_recall=macro_r,
            macro_f1=macro_f,
            weighted_f1=weight_f,
            abstention_rate=abstention_rate,
            ood_rejection_rate=ood_rate,
            low_confidence_rate=low_conf_rate,
            mean_confidence=mean_conf,
            median_confidence=median_conf,
            confidence_buckets=buckets,
            confusion_matrix=cm,
            per_class_metrics=rep,
            benchmark_accuracy=benchmark_accuracy,
            benchmark_macro_f1=benchmark_macro_f1,
            delta_accuracy=delta_acc,
            delta_macro_f1=delta_f1,
            current_status=status,
            field_validation_statement=statement,
            high_confidence_error_count=high_conf_errs,
            low_confidence_correct_count=low_conf_corr,
            probable_accuracy=prob_acc,
            probable_macro_f1=prob_f1,
            failure_cases=failure_cases,
            farm_count=len(farms),
            plant_count=len(plants),
            session_count=len(sessions),
            device_count=len(devices),
            multi_disease_unsupported_count=multi_disease_count,
            group_level_metrics=group_metrics,
            edge_vs_server_parity={}
        )
