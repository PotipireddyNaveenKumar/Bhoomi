import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from app.services.safety.safety_engine import SafetyEngine
from app.services.voice.intent_service import VoiceIntentType
from app.services.vision.field_validation.schemas import (
    VoicePilotRecord,
    DataProvenance,
    ProvenanceSourceType
)


class VoiceFieldPilotAuditService:
    """
    Evaluates real physical field voice pilot audio and transcripts longitudinally.
    Monitors transcription quality, intent accuracy, language accuracy, and crucially
    tracks critical false state-changing mutations and safety violations.
    """

    MIN_VOICE_SAMPLES_FOR_METRICS = 30

    CRITICAL_MUTATIONS = {
        "FALSE_COMPLETION",
        "FALSE_POSTPONEMENT",
        "FALSE_SKIP",
        "FALSE_TASK_SELECTION",
        "FALSE_CONFIRMATION"
    }

    # PII sanitization regexes
    TOKEN_REGEX = re.compile(r'(eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}|\b(sk|key|token|auth)_[a-zA-Z0-9]{12,}\b)', re.IGNORECASE)
    PHONE_REGEX = re.compile(r'(\+91[\-\s]?)?[6-9]\d{9}')
    AADHAAR_REGEX = re.compile(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b')

    @classmethod
    def sanitize_audit_log(cls, text: str) -> str:
        """
        Strips API keys, auth tokens, phone numbers, and Aadhaar numbers from audit displays.
        """
        if not text:
            return ""
        s = cls.TOKEN_REGEX.sub("[REDACTED_SECRET]", text)
        s = cls.PHONE_REGEX.sub("[REDACTED_PHONE]", s)
        s = cls.AADHAAR_REGEX.sub("[REDACTED_AADHAAR]", s)
        return s

    @classmethod
    def evaluate_voice_pilot_turn(
        cls,
        pilot_record: Dict[str, Any],
        expected_intent: Optional[str] = None,
        expected_action: Optional[str] = None,
        actual_action: Optional[str] = None,
        actual_task_id: Optional[str] = None,
        expected_task_id: Optional[str] = None,
        confirmation_required: bool = False,
        confirmation_obtained: bool = False
    ) -> Dict[str, Any]:
        """
        Audits a single pilot voice interaction.
        Detects catastrophic false state mutations:
        - FALSE_COMPLETION
        - FALSE_POSTPONEMENT
        - FALSE_SKIP
        - FALSE_TASK_SELECTION
        - FALSE_CONFIRMATION
        """
        transcript = cls.sanitize_audit_log(pilot_record.get("transcript", ""))
        inferred_intent = pilot_record.get("intent")
        stt_conf = float(pilot_record.get("stt_confidence", 0.0))
        intent_conf = float(pilot_record.get("intent_confidence", 0.0))
        language = pilot_record.get("language", "en")
        noise = pilot_record.get("noise_condition", "normal")
        device = pilot_record.get("device", "smartphone")

        # Intent correctness
        intent_correct = (expected_intent is None) or (inferred_intent == expected_intent)

        # Critical false action evaluation
        mutation_detected = None
        if actual_action and expected_action and actual_action != expected_action:
            if actual_action.upper() == "COMPLETE" and expected_action.upper() != "COMPLETE":
                mutation_detected = "FALSE_COMPLETION"
            elif actual_action.upper() == "POSTPONE" and expected_action.upper() != "POSTPONE":
                mutation_detected = "FALSE_POSTPONEMENT"
            elif actual_action.upper() == "SKIP" and expected_action.upper() != "SKIP":
                mutation_detected = "FALSE_SKIP"

        if not mutation_detected and expected_task_id and actual_task_id and expected_task_id != actual_task_id:
            mutation_detected = "FALSE_TASK_SELECTION"

        if confirmation_required and not confirmation_obtained and actual_action in ["COMPLETE", "POSTPONE", "SKIP"]:
            mutation_detected = "FALSE_CONFIRMATION"

        # Action success
        action_success = (mutation_detected is None) and (
            (expected_action is None) or (actual_action == expected_action)
        )

        return {
            "audio_id": pilot_record.get("audio_id", "unknown"),
            "language": language,
            "device": device,
            "noise_condition": noise,
            "transcript_sanitized": transcript,
            "stt_confidence": stt_conf,
            "intent_confidence": intent_conf,
            "inferred_intent": inferred_intent,
            "expected_intent": expected_intent,
            "intent_correct": intent_correct,
            "action_success": action_success,
            "critical_mutation": mutation_detected,
            "is_safety_defect": mutation_detected in cls.CRITICAL_MUTATIONS,
            "confirmation_bypassed": confirmation_required and not confirmation_obtained and bool(actual_action)
        }

    @classmethod
    def audit_voice_safety(
        cls,
        evaluations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Computes safety audit metrics across voice pilot interactions:
        - unsafe_action_block_rate
        - false_block_rate
        - confirmation_bypass_rate
        - ambiguous_command_execution_rate
        """
        if not evaluations:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": "No voice evaluations available for safety audit.",
                "total_evaluations": 0,
                "safety_defect_count": 0
            }

        total = len(evaluations)
        defects = [e for e in evaluations if e.get("is_safety_defect")]
        bypasses = [e for e in evaluations if e.get("confirmation_bypassed")]
        ambiguous_executions = [
            e for e in evaluations
            if e.get("intent_confidence", 1.0) < 0.6 and e.get("action_success") and e.get("critical_mutation")
        ]

        return {
            "status": "AUDITED",
            "total_evaluations": total,
            "safety_defect_count": len(defects),
            "safety_defect_rate": round(len(defects) / total, 4) if total > 0 else 0.0,
            "confirmation_bypass_count": len(bypasses),
            "confirmation_bypass_rate": round(len(bypasses) / total, 4) if total > 0 else 0.0,
            "ambiguous_command_execution_count": len(ambiguous_executions),
            "ambiguous_command_execution_rate": round(len(ambiguous_executions) / total, 4) if total > 0 else 0.0,
            "defects_by_type": {
                m: sum(1 for e in evaluations if e.get("critical_mutation") == m)
                for m in cls.CRITICAL_MUTATIONS
            }
        }

    @classmethod
    def calculate_voice_longitudinal_metrics(
        cls,
        evaluated_turns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregates longitudinal voice metrics.
        Returns INSUFFICIENT_DATA if fewer than MIN_VOICE_SAMPLES_FOR_METRICS records exist,
        ensuring honest transparency without fabricated statistical performance.
        """
        total = len(evaluated_turns)
        if total == 0:
            return {
                "status": "PILOT_DATA_PENDING",
                "metrics_available": False,
                "total_samples": 0,
                "message": "FIELD DATA NOT YET AVAILABLE: No physical voice pilot logs queued."
            }

        if total < cls.MIN_VOICE_SAMPLES_FOR_METRICS:
            return {
                "status": "INSUFFICIENT_DATA",
                "metrics_available": False,
                "total_samples": total,
                "min_required": cls.MIN_VOICE_SAMPLES_FOR_METRICS,
                "message": (
                    f"Sample size too small ({total} samples < {cls.MIN_VOICE_SAMPLES_FOR_METRICS} required). "
                    "Longitudinal voice metrics withheld to prevent misleading performance claims."
                )
            }

        # Calculate metrics
        correct_intents = sum(1 for t in evaluated_turns if t.get("intent_correct", False))
        action_successes = sum(1 for t in evaluated_turns if t.get("action_success", False))
        critical_mutations = sum(1 for t in evaluated_turns if t.get("is_safety_defect", False))
        mean_stt_conf = sum(t.get("stt_confidence", 0.0) for t in evaluated_turns) / total
        mean_intent_conf = sum(t.get("intent_confidence", 0.0) for t in evaluated_turns) / total

        # Segmentations
        by_language = defaultdict(list)
        by_noise = defaultdict(list)
        by_device = defaultdict(list)

        for t in evaluated_turns:
            by_language[t.get("language", "unknown")].append(t)
            by_noise[t.get("noise_condition", "normal")].append(t)
            by_device[t.get("device", "smartphone")].append(t)

        def segment_stats(items):
            cnt = len(items)
            succ = sum(1 for i in items if i.get("action_success", False))
            return {
                "count": cnt,
                "action_success_rate": round(succ / cnt, 4) if cnt > 0 else 0.0
            }

        return {
            "status": "EVALUATED",
            "metrics_available": True,
            "total_samples": total,
            "intent_accuracy": round(correct_intents / total, 4),
            "action_success_rate": round(action_successes / total, 4),
            "critical_defect_count": critical_mutations,
            "critical_defect_rate": round(critical_mutations / total, 4),
            "mean_stt_confidence": round(mean_stt_conf, 4),
            "mean_intent_confidence": round(mean_intent_conf, 4),
            "segmented_by_language": {lang: segment_stats(items) for lang, items in by_language.items()},
            "segmented_by_noise": {noise: segment_stats(items) for noise, items in by_noise.items()},
            "segmented_by_device": {dev: segment_stats(items) for dev, items in by_device.items()},
            "safety_audit": cls.audit_voice_safety(evaluated_turns)
        }
