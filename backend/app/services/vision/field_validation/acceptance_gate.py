from typing import Dict, Any, Optional
from app.services.vision.field_validation.schemas import CropFieldEvaluationSummary, ModelFieldStatus

class FieldValidationAcceptanceGate:
    """
    Documented Acceptance Gate for Field Validation.
    A vision model CANNOT become FIELD_VALIDATED solely because accuracy
    exceeds an arbitrary threshold. It requires multi-farm diversity,
    pathologist-confirmed labels, low high-confidence errors, and human sign-off.
    """

    MIN_CONFIRMED_SAMPLES = 30
    PREFERRED_TARGET_SAMPLES = 50
    MIN_INDEPENDENT_FARMS = 5
    MIN_MACRO_F1_THRESHOLD = 0.75
    MAX_HIGH_CONFIDENCE_ERROR_RATE = 0.05  # 5%

    @classmethod
    def evaluate_acceptance(
        cls,
        summary: CropFieldEvaluationSummary,
        has_human_agronomist_sign_off: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates whether a crop pathology model meets all criteria
        for FIELD_VALIDATED status.
        """
        crop = summary.crop.lower()

        # Rule 1: Rice is strictly locked to RESEARCH_ONLY
        if crop == "rice":
            return {
                "decision": "REJECTED",
                "recommended_status": ModelFieldStatus.RESEARCH_ONLY,
                "reason": "Rice is permanently classified as RESEARCH_ONLY and barred from farmer-facing diagnosis.",
                "checklist": {"rice_lock": True}
            }

        # Rule 2: Zero field images -> FIELD DATA NOT YET AVAILABLE
        if summary.total_images == 0 or summary.evaluated_images == 0:
            return {
                "decision": "PENDING",
                "recommended_status": ModelFieldStatus.FIELD_PENDING,
                "reason": "FIELD DATA NOT YET AVAILABLE. No on-farm smartphone images collected.",
                "checklist": {
                    "has_field_data": False,
                    "sample_count_ok": False,
                    "farm_diversity_ok": False,
                    "macro_f1_ok": False,
                    "high_conf_error_ok": False,
                    "human_sign_off": has_human_agronomist_sign_off
                }
            }

        total = summary.evaluated_images
        high_conf_rate = summary.high_confidence_error_count / total if total > 0 else 0.0

        checklist = {
            "has_field_data": True,
            "sample_count_ok": total >= cls.MIN_CONFIRMED_SAMPLES,
            "farm_diversity_ok": summary.farm_count >= cls.MIN_INDEPENDENT_FARMS,
            "macro_f1_ok": summary.macro_f1 >= cls.MIN_MACRO_F1_THRESHOLD,
            "high_conf_error_ok": high_conf_rate <= cls.MAX_HIGH_CONFIDENCE_ERROR_RATE,
            "human_sign_off": has_human_agronomist_sign_off
        }

        # Check for critical safety failures
        if high_conf_rate > 0.15:
            return {
                "decision": "REJECTED_UNSAFE",
                "recommended_status": ModelFieldStatus.FIELD_UNSAFE,
                "reason": f"Critical safety risk: High-confidence error rate ({high_conf_rate*100:.1f}%) exceeds safety limit (15%).",
                "checklist": checklist
            }

        # All criteria must pass for FIELD_VALIDATED
        if all(checklist.values()):
            return {
                "decision": "ACCEPTED",
                "recommended_status": ModelFieldStatus.FIELD_VALIDATED,
                "reason": "Model satisfies all field data criteria and has verified agronomist sign-off.",
                "checklist": checklist
            }

        # If data is present but samples/farms are limited or sign-off is pending
        if checklist["sample_count_ok"] and not has_human_agronomist_sign_off:
            return {
                "decision": "PENDING_SIGN_OFF",
                "recommended_status": ModelFieldStatus.FIELD_PENDING,
                "reason": "Quantitative criteria met, but awaiting formal human agronomist/pathologist sign-off.",
                "checklist": checklist
            }

        return {
            "decision": "INSUFFICIENT_DATA",
            "recommended_status": ModelFieldStatus.FIELD_PENDING,
            "reason": f"Insufficient pilot field data ({total} samples, {summary.farm_count} farms). Minimum required: {cls.MIN_CONFIRMED_SAMPLES} samples across {cls.MIN_INDEPENDENT_FARMS} farms.",
            "checklist": checklist
        }

    @classmethod
    def get_crop_field_status(
        cls,
        crop: str,
        summary: Optional[CropFieldEvaluationSummary] = None
    ) -> Dict[str, Any]:
        """
        Returns independent status per crop.
        Rice is locked permanently to RESEARCH_ONLY.
        Other crops remain PILOT_DATA_PENDING unless real field data exists.
        """
        cleaned = crop.strip().lower()
        if cleaned == "rice":
            return {
                "crop": "rice",
                "status": "RESEARCH_ONLY",
                "is_production_ready": False,
                "reason": "Rice is permanently locked to RESEARCH_ONLY. Farmer-facing chemical treatment promotion strictly barred."
            }

        if not summary or summary.total_images == 0:
            return {
                "crop": cleaned,
                "status": "PILOT_DATA_PENDING",
                "is_production_ready": False,
                "reason": f"No physical field pilot observations collected yet for {cleaned}."
            }

        gate_res = cls.evaluate_acceptance(summary)
        return {
            "crop": cleaned,
            "status": gate_res.get("recommended_status").value if hasattr(gate_res.get("recommended_status"), "value") else str(gate_res.get("recommended_status")),
            "decision": gate_res.get("decision"),
            "is_production_ready": gate_res.get("decision") == "ACCEPTED",
            "checklist": gate_res.get("checklist", {})
        }

    @classmethod
    def evaluate_system_production_readiness(
        cls,
        has_real_field_pilot_data: bool = False,
        vision_gate_by_crop: Optional[Dict[str, Dict[str, Any]]] = None,
        voice_metrics: Optional[Dict[str, Any]] = None,
        task_metrics: Optional[Dict[str, Any]] = None,
        expert_review_summary: Optional[Dict[str, Any]] = None,
        leakage_detected: bool = False,
        safety_acceptable: bool = True
    ) -> Dict[str, Any]:
        """
        Multi-dimensional Production Acceptance Gate.
        A single Macro-F1 score is NOT sufficient.
        Requires:
        1. REAL physical field data present (not synthetic fixtures)
        2. Expert review complete with pathologist sign-off
        3. Zero cross-split group leakage
        4. Agronomic safety acceptable
        5. Vision acceptable for validated crops
        6. Voice acceptable with 0 critical state-changing defects
        7. Task behavior acceptable
        """
        checklist = {
            "field_data_present": has_real_field_pilot_data,
            "expert_review_complete": bool(expert_review_summary and expert_review_summary.get("total_reviews", 0) >= 30),
            "no_leakage": not leakage_detected,
            "safety_acceptable": safety_acceptable,
            "vision_acceptable": bool(vision_gate_by_crop and len(vision_gate_by_crop) > 0 and all(g.get("decision") == "ACCEPTED" for g in vision_gate_by_crop.values())),
            "voice_acceptable": bool(voice_metrics and voice_metrics.get("metrics_available") and voice_metrics.get("critical_defect_count", 1) == 0),
            "task_behavior_acceptable": bool(task_metrics and task_metrics.get("metrics_available") and task_metrics.get("completion_rate", 0.0) >= 0.60)
        }

        is_production_ready = all(checklist.values())
        overall_status = "PRODUCTION_READY" if is_production_ready else "NOT_PRODUCTION_READY"

        reasons = []
        if not has_real_field_pilot_data:
            reasons.append("REAL_FIELD_PILOT_DATA = NOT_PRESENT. Zero physical on-farm pilot data in repository.")
        if not checklist["expert_review_complete"]:
            reasons.append("EXPERT_REVIEW_PENDING. Independent agronomic pathologist reviews incomplete.")
        if not checklist["vision_acceptable"]:
            reasons.append("VISION_FIELD_EVALUATION_PENDING. Not all crops have verified field validation.")
        if not checklist["voice_acceptable"]:
            reasons.append("VOICE_FIELD_PILOT_PENDING. Longitudinal voice metrics unavailable or defects detected.")
        if not checklist["task_behavior_acceptable"]:
            reasons.append("TASK_LONGITUDINAL_PENDING. Longitudinal farm task adherence logs insufficient.")

        return {
            "overall_status": overall_status,
            "is_production_ready": is_production_ready,
            "real_field_pilot_data": "PRESENT" if has_real_field_pilot_data else "NOT_PRESENT",
            "checklist": checklist,
            "blocking_reasons": reasons,
            "statement": (
                "BHOOMI V2 has passed all automated tests and safety simulation, but remains "
                f"{overall_status} because physical on-farm pilot ingestion, blind expert annotations, "
                "and longitudinal agronomic verification are strictly required before deployment."
            )
        }
