import os
import io
import json
import pytest
from datetime import datetime, timezone, timedelta
from PIL import Image
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.vision.field_validation.schemas import (
    FieldImageMetadata,
    ExpertLabelRecord,
    AnnotationState,
    ModelFieldStatus,
    DuplicateClassification,
    ProvenanceSourceType,
    DataProvenance,
    VoicePilotRecord,
    TaskOutcomeRecord,
    ExpertReviewClassification,
    RAGSourceAuditFlag
)
from app.services.vision.field_validation.validator import FieldDatasetValidator
from app.services.vision.field_validation.ingest import FieldPilotIngestionService
from app.services.vision.field_validation.group_evaluator import FarmSessionGroupManager
from app.services.vision.field_validation.acceptance_gate import FieldValidationAcceptanceGate
from app.services.voice.field_audit import VoiceFieldPilotAuditService
from app.services.farm_manager.longitudinal_audit import (
    TaskLongitudinalAuditService,
    RecommendationOutcomeAuditService,
    AgronomicExpertReviewService,
    RAGSourceAuditService,
    AgronomicSafetyAuditor
)
from app.services.monitoring.pilot_drift import PilotDriftDetector
from app.services.farm_manager.task_engine import TaskIntelligenceEngine, FarmTask, TaskType, TaskStatus
from app.schemas.decision import DecisionPriority


def make_test_fixture_image(color=(40, 140, 40), size=(128, 128)) -> bytes:
    """TEST_FIXTURE image generator strictly marked for test use only."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ============================================================================
# CATEGORY A: VALID IMAGE INGESTION
# ============================================================================
def test_valid_image_ingestion():
    raw_bytes = make_test_fixture_image()
    metadata = {
        "image_id": "TEST_FIXTURE_IMG_001",
        "crop": "tomato",
        "image_path": "test_leaf.jpg",
        "actual_disease": "early_blight",
        "location": "Guntur Region",
        "state": "Andhra Pradesh",
        "district": "Guntur",
        "crop_stage": "vegetative",
        "lighting_condition": "diffuse_daylight",
        "camera_device": "Redmi 9A",
        "image_distance": "moderate_leaf_span",
        "leaf_condition": "fresh_attached",
        "occlusion_level": "none",
        "image_quality": "PASSED",
        "expert_label": "Tomato___Early_blight",
        "annotator_confidence": 0.95,
        "annotation_source": "ANGRAU Pathologist",
        "annotation_date": "2026-09-04",
        "farmer_id_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90",
        "farm_id_hash": "f1f2f3f4f5f60718293a4b5c6d7e8f91",
        "source_type": "FARMER_CAPTURED"
    }
    expert = {
        "image_id": "TEST_FIXTURE_IMG_001",
        "crop": "tomato",
        "expert_label": "Tomato___Early_blight",
        "annotation_state": "CONFIRMED",
        "expert_id": "EXP_001",
        "review_date": "2026-09-04"
    }

    res = FieldPilotIngestionService.ingest_single_image(
        image_bytes=raw_bytes,
        filename="test_leaf.jpg",
        metadata=metadata,
        expert_label=expert
    )

    assert res["status"] == "ACCEPTED"
    assert res["accepted"] is True
    assert res["duplicate_classification"] == "UNIQUE"
    assert res["manifest_item"]["crop"] == "tomato"
    assert res["manifest_item"]["included_in_evaluation"] is True


# ============================================================================
# CATEGORY B: INVALID IMAGE INGESTION (CORRUPT/ZERO-BYTE/SIZE)
# ============================================================================
def test_invalid_image_ingestion_quarantined():
    # Test zero-byte corrupt input
    res = FieldPilotIngestionService.ingest_single_image(
        image_bytes=b"",
        filename="empty.jpg",
        metadata={"image_id": "TEST_FIXTURE_EMPTY", "crop": "tomato"}
    )
    assert res["status"] == "QUARANTINED"
    assert res["accepted"] is False
    assert any("empty" in r for r in res["rejection_reasons"])

    # Test corrupted image bytes
    res_corrupt = FieldPilotIngestionService.ingest_single_image(
        image_bytes=b"NOT_A_REAL_IMAGE_DATA_CORRUPT",
        filename="corrupt.jpg",
        metadata={"image_id": "TEST_FIXTURE_CORRUPT", "crop": "tomato"}
    )
    assert res_corrupt["status"] == "QUARANTINED"
    assert res_corrupt["accepted"] is False
    assert any("decode failure" in r or "Corrupt" in r for r in res_corrupt["rejection_reasons"])


# ============================================================================
# CATEGORY C: EXACT DUPLICATE REJECTION
# ============================================================================
def test_exact_duplicate_rejection():
    raw_bytes = make_test_fixture_image()
    # Compute MD5
    _, _, info = FieldDatasetValidator.validate_media_file(raw_bytes)
    md5_hash = info["md5_hash"]

    metadata = {
        "image_id": "TEST_FIXTURE_DUP_002",
        "crop": "tomato",
        "image_path": "dup.jpg",
        "actual_disease": "healthy",
        "location": "Farm 1",
        "state": "AP",
        "district": "Guntur",
        "crop_stage": "flowering",
        "lighting_condition": "normal",
        "camera_device": "Samsung",
        "image_distance": "close",
        "leaf_condition": "attached",
        "occlusion_level": "none",
        "image_quality": "PASSED",
        "expert_label": "Tomato___healthy",
        "annotator_confidence": 0.9,
        "annotation_source": "KVK",
        "annotation_date": "2026-09-04",
        "farmer_id_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    }

    # Pass known exact hash
    res = FieldPilotIngestionService.ingest_single_image(
        image_bytes=raw_bytes,
        filename="dup.jpg",
        metadata=metadata,
        known_exact_hashes={md5_hash: ["original_file.jpg", "dup.jpg"]}
    )

    assert res["status"] == "QUARANTINED"
    assert res["accepted"] is False
    assert res["duplicate_classification"] == DuplicateClassification.EXACT_DUPLICATE.value
    assert any("Exact duplicate" in r for r in res["rejection_reasons"])


# ============================================================================
# CATEGORY D: NEAR-DUPLICATE FLAGGING
# ============================================================================
def test_near_duplicate_flagging():
    raw_bytes = make_test_fixture_image()
    metadata = {
        "image_id": "TEST_FIXTURE_NEAR_003",
        "crop": "tomato",
        "image_path": "near.jpg",
        "actual_disease": "healthy",
        "location": "Farm 1",
        "state": "AP",
        "district": "Guntur",
        "crop_stage": "flowering",
        "lighting_condition": "normal",
        "camera_device": "Samsung",
        "image_distance": "close",
        "leaf_condition": "attached",
        "occlusion_level": "none",
        "image_quality": "PASSED",
        "expert_label": "Tomato___healthy",
        "annotator_confidence": 0.9,
        "annotation_source": "KVK",
        "annotation_date": "2026-09-04",
        "farmer_id_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    }
    expert = {
        "image_id": "TEST_FIXTURE_NEAR_003",
        "crop": "tomato",
        "expert_label": "Tomato___healthy",
        "annotation_state": "CONFIRMED",
        "expert_id": "EXP_001",
        "review_date": "2026-09-04"
    }

    res = FieldPilotIngestionService.ingest_single_image(
        image_bytes=raw_bytes,
        filename="near.jpg",
        metadata=metadata,
        expert_label=expert,
        near_dup_paths={"near.jpg"}
    )

    assert res["duplicate_classification"] == DuplicateClassification.NEAR_DUPLICATE.value
    # Near duplicates are flagged but not silently discarded
    assert res["manifest_item"]["duplicate_status"] == "FLAG_NEAR_DUPLICATE"


# ============================================================================
# CATEGORY E: PII DETECTION (PHONE, AADHAAR, ADDRESS)
# ============================================================================
def test_pii_detection():
    # Phone number leak
    rec1 = {"location": "Village near +91 9876543210"}
    clean1, err1 = FieldDatasetValidator.validate_privacy(rec1)
    assert clean1 is False
    assert any("Phone" in e for e in err1)

    # 12-digit Aadhaar leak
    rec2 = {"notes": "Farmer Aadhaar is 1234 5678 9012"}
    clean2, err2 = FieldDatasetValidator.validate_privacy(rec2)
    assert clean2 is False
    assert any("Aadhaar" in e for e in err2)

    # Survey number leak
    rec3 = {"notes": "Collected from survey no 145/2"}
    clean3, err3 = FieldDatasetValidator.validate_privacy(rec3)
    assert clean3 is False
    assert any("survey" in e.lower() for e in err3)


# ============================================================================
# CATEGORY F: METADATA VALIDATION
# ============================================================================
def test_metadata_validation():
    # Invalid crop
    bad_meta = {
        "image_id": "TEST_FIXTURE_BAD_CROP",
        "crop": "unsupported_dragonfruit",
        "image_path": "x.jpg"
    }
    clean, errors = FieldDatasetValidator.validate_metadata_record(bad_meta)
    assert clean is False
    assert any("Invalid crop" in e for e in errors)


# ============================================================================
# CATEGORY G: DATA PROVENANCE
# ============================================================================
def test_data_provenance_immutability():
    rec = RecommendationOutcomeAuditService.create_audit_record(
        recommendation_trace_id="TRACE_PROV_123",
        crop="chilli",
        system_recommendation={"action": "spray_neem"},
        farm_state_snapshot={"moisture": 55},
        farmer_action="sprayed_neem",
        farmer_reported_outcome="thrips_reduced",
        expert_verification="confirmed_beneficial"
    )
    assert rec.provenance.source_type == ProvenanceSourceType.SYSTEM_GENERATED
    assert rec.final_outcome is None  # Never collapsed prematurely
    assert rec.expert_verification == "confirmed_beneficial"


# ============================================================================
# CATEGORY H: MANIFEST & QUALITY REPORT GENERATION
# ============================================================================
def test_manifest_and_quality_report_empty():
    manifest = FieldPilotIngestionService.ingest_pilot_batch(
        metadata_csv="data/field_validation/metadata/non_existent.csv",
        labels_csv="data/field_validation/labels/non_existent.csv",
        manifest_dir="data/field_validation/manifests"
    )
    assert manifest.total_submitted == 0
    assert manifest.quality_report is not None
    assert manifest.quality_report["total_records"] == 0
    assert manifest.quality_report["accepted"] == 0


# ============================================================================
# CATEGORY I: SPLIT LEAKAGE PREVENTION (THREE-WAY GROUP ISOLATION)
# ============================================================================
def test_split_leakage_prevention():
    records = [
        {"image_id": f"IMG_{i}", "farm_id_hash": f"farm_hash_{i % 5}", "plant_id_hash": f"plant_hash_{i % 10}"}
        for i in range(50)
    ]
    splits = FarmSessionGroupManager.group_aware_three_way_split(records, train_ratio=0.6, val_ratio=0.2)
    assert len(splits["train"]) > 0
    assert len(splits["validation"]) > 0
    assert len(splits["test"]) > 0

    leakage_audit = FarmSessionGroupManager.detect_three_way_leakage(
        train_set=splits["train"],
        val_set=splits["validation"],
        test_set=splits["test"]
    )
    assert leakage_audit["has_leakage"] is False


# ============================================================================
# CATEGORY J: BLIND EXPERT ANNOTATION
# ============================================================================
def test_blind_expert_annotation_isolation():
    raw_observation = {
        "image_id": "TEST_FIXTURE_BLIND_001",
        "crop": "tomato",
        "lighting_condition": "diffuse",
        "predicted_disease": "Tomato___Early_blight",
        "confidence": 0.94,
        "calibrated_confidence": 0.92,
        "model_name": "MobileNetV3"
    }

    blind_packet = FarmSessionGroupManager.prepare_blind_annotation_packet(raw_observation)
    assert "predicted_disease" not in blind_packet
    assert "confidence" not in blind_packet
    assert "model_name" not in blind_packet
    assert blind_packet["is_blinded"] is True
    assert blind_packet["crop"] == "tomato"


# ============================================================================
# CATEGORY K & L: FIELD METRICS & INSUFFICIENT-DATA HANDLING
# ============================================================================
def test_insufficient_data_handling_honest_withholding():
    # 5 samples (< MIN 30)
    samples = [{"image_id": f"IMG_{i}", "predicted_disease": "healthy", "expert_label": "healthy"} for i in range(5)]
    res = FarmSessionGroupManager.aggregate_group_predictions(samples, min_groups_required=30)
    assert res["group_metrics_available"] is False
    assert res["status"] == "GROUP-LEVEL METRICS NOT YET RELIABLE"
    assert "withheld" in res["message"]


# ============================================================================
# CATEGORY M: FIELD DOMAIN SHIFT
# ============================================================================
def test_domain_shift_detection():
    # Sample count < 30 returns INSUFFICIENT_SAMPLE_SIZE
    insufficient = PilotDriftDetector.detect_vision_drift(
        benchmark_stats={"accuracy": 0.95, "macro_f1": 0.92},
        field_stats={"accuracy": 0.70, "macro_f1": 0.65, "total_samples": 10},
        min_samples=30
    )
    assert insufficient["drift_detected"] is False
    assert insufficient["status"] == "INSUFFICIENT_SAMPLE_SIZE"

    # Sample count >= 30 with severe drop triggers drift
    drift = PilotDriftDetector.detect_vision_drift(
        benchmark_stats={"accuracy": 0.95, "macro_f1": 0.92, "mean_confidence": 0.90},
        field_stats={"accuracy": 0.72, "macro_f1": 0.68, "mean_confidence": 0.60, "total_samples": 40},
        min_samples=30
    )
    assert drift["drift_detected"] is True
    assert drift["status"] == "DRIFT_DETECTED"
    assert drift["shifts"]["accuracy_shift"] == -0.23


# ============================================================================
# CATEGORY N & O: VOICE FIELD METRICS & FALSE STATE-CHANGING ACTIONS
# ============================================================================
def test_false_state_changing_voice_actions():
    # 1. FALSE_COMPLETION defect
    defect_comp = VoiceFieldPilotAuditService.evaluate_voice_pilot_turn(
        pilot_record={"audio_id": "AUD_01", "language": "te", "transcript": "నేను పని చేయలేదు", "stt_confidence": 0.8},
        expected_action="NONE",
        actual_action="COMPLETE"
    )
    assert defect_comp["critical_mutation"] == "FALSE_COMPLETION"
    assert defect_comp["is_safety_defect"] is True

    # 2. FALSE_POSTPONEMENT defect
    defect_post = VoiceFieldPilotAuditService.evaluate_voice_pilot_turn(
        pilot_record={"audio_id": "AUD_02", "language": "hi", "transcript": "सिंचाई कब करनी है?", "stt_confidence": 0.8},
        expected_action="QUERY",
        actual_action="POSTPONE"
    )
    assert defect_post["critical_mutation"] == "FALSE_POSTPONEMENT"
    assert defect_post["is_safety_defect"] is True

    # 3. FALSE_TASK_SELECTION defect
    defect_sel = VoiceFieldPilotAuditService.evaluate_voice_pilot_turn(
        pilot_record={"audio_id": "AUD_03", "language": "en", "transcript": "Completed scouting", "stt_confidence": 0.9},
        expected_action="COMPLETE",
        actual_action="COMPLETE",
        expected_task_id="task_scout_1",
        actual_task_id="task_pesticide_spraying_urgent"
    )
    assert defect_sel["critical_mutation"] == "FALSE_TASK_SELECTION"
    assert defect_sel["is_safety_defect"] is True


# ============================================================================
# CATEGORY P: VOICE SAFETY AUDIT
# ============================================================================
def test_voice_safety_audit():
    turns = [
        {"audio_id": "1", "is_safety_defect": True, "critical_mutation": "FALSE_COMPLETION", "confirmation_bypassed": True},
        {"audio_id": "2", "is_safety_defect": False, "critical_mutation": None, "confirmation_bypassed": False}
    ]
    safety_audit = VoiceFieldPilotAuditService.audit_voice_safety(turns)
    assert safety_audit["total_evaluations"] == 2
    assert safety_audit["safety_defect_count"] == 1
    assert safety_audit["confirmation_bypass_count"] == 1
    assert safety_audit["defects_by_type"]["FALSE_COMPLETION"] == 1


# ============================================================================
# CATEGORY Q: TASK LONGITUDINAL ADHERENCE AUDIT
# ============================================================================
def test_task_longitudinal_adherence_audit():
    # Empty logs -> PILOT_DATA_PENDING
    empty_res = TaskLongitudinalAuditService.calculate_task_metrics([])
    assert empty_res["status"] == "PILOT_DATA_PENDING"
    assert empty_res["metrics_available"] is False

    # Insufficient logs (< 30) -> INSUFFICIENT_DATA
    few_logs = [{"task_id": f"T_{i}", "completed_at": "2026-09-04"} for i in range(10)]
    insuf_res = TaskLongitudinalAuditService.calculate_task_metrics(few_logs)
    assert insuf_res["status"] == "INSUFFICIENT_DATA"
    assert insuf_res["metrics_available"] is False

    # 35 logs -> EVALUATED
    logs_35 = [
        {"task_id": f"T_{i}", "crop": "Chilli", "task_type": "IRRIGATION", "due_at": "2026-09-01", "completed_at": "2026-09-02"}
        for i in range(35)
    ]
    eval_res = TaskLongitudinalAuditService.calculate_task_metrics(logs_35)
    assert eval_res["status"] == "EVALUATED"
    assert eval_res["metrics_available"] is True
    assert eval_res["completion_rate"] == 1.0
    assert eval_res["median_completion_delay_days"] == 1.0


# ============================================================================
# CATEGORY R: RECOMMENDATION TRACE PROVENANCE
# ============================================================================
def test_recommendation_trace_provenance():
    audit_rec = RecommendationOutcomeAuditService.create_audit_record(
        recommendation_trace_id="TRACE_REC_999",
        crop="tomato",
        system_recommendation={"advice": "Monitor moisture"},
        farm_state_snapshot={"soil_moisture": 42}
    )
    assert audit_rec.provenance.source_reference == "TRACE_REC_999"
    assert audit_rec.provenance.source_type == ProvenanceSourceType.SYSTEM_GENERATED


# ============================================================================
# CATEGORY S: INDEPENDENT AGRONOMIC EXPERT REVIEW
# ============================================================================
def test_agronomic_expert_review_workflow():
    review = AgronomicExpertReviewService.submit_expert_review(
        recommendation_id="REC_001",
        expert_id_hash="e1e2e3e4e5e6e7e8e9e0123456789012",
        classification=ExpertReviewClassification.SAFETY_CONCERN,
        crop="Tomato",
        crop_stage="flowering",
        evidence_evaluated={"weather": "high humidity"},
        explanation="Flowering stage chemical application risks blossom drop.",
        correction="Switch to bio-fungicide Bacillus subtilis."
    )
    assert review.classification == ExpertReviewClassification.SAFETY_CONCERN
    assert review.original_recommendation_preserved is True
    assert "blossom drop" in review.explanation

    summary = AgronomicExpertReviewService.get_expert_review_summary()
    assert summary["safety_concerns_raised"] >= 1


# ============================================================================
# CATEGORY T: RAG / SOURCE AUDIT
# ============================================================================
def test_rag_source_audit():
    # Valid high-authority citation
    valid_audit = RAGSourceAuditService.audit_rag_source(
        trace_id="TR_1",
        crop="Tomato",
        state="Andhra Pradesh",
        source_citation="ICAR-IIHR Tomato Disease Management SOP, Andhra Pradesh, 2025"
    )
    assert valid_audit.flag == RAGSourceAuditFlag.VALID
    assert valid_audit.source_authority == "high"

    # Low-authority source
    low_auth_audit = RAGSourceAuditService.audit_rag_source(
        trace_id="TR_2",
        crop="Tomato",
        state="Andhra Pradesh",
        source_citation="Generic Gardening Blog Tomato Tips"
    )
    assert low_auth_audit.flag == RAGSourceAuditFlag.LOW_AUTHORITY_SOURCE

    # Crop mismatch
    crop_mismatch_audit = RAGSourceAuditService.audit_rag_source(
        trace_id="TR_3",
        crop="Tomato",
        state="Andhra Pradesh",
        source_citation="ICAR Sugarcane Borer Control Guide"
    )
    assert crop_mismatch_audit.flag == RAGSourceAuditFlag.CROP_MISMATCH


# ============================================================================
# CATEGORY U: RICE PROTECTION
# ============================================================================
def test_rice_permanent_research_only_protection():
    # Gate check
    rice_status = FieldValidationAcceptanceGate.get_crop_field_status("rice")
    assert rice_status["status"] == "RESEARCH_ONLY"
    assert rice_status["is_production_ready"] is False
    assert "RESEARCH_ONLY" in rice_status["reason"]

    # Safety auditor check
    safety_res = AgronomicSafetyAuditor.audit_recommendation_safety(
        crop="rice",
        crop_stage="vegetative",
        recommendation_text="Spray 2.5ml systemic fungicide for blast control."
    )
    assert safety_res["is_safe"] is False
    assert safety_res["rice_research_only_locked"] is True
    assert any("CRITICAL RICE VIOLATION" in v for v in safety_res["violations"])


# ============================================================================
# CATEGORY V: DETERMINISTIC DRIFT DETECTION
# ============================================================================
def test_pilot_drift_detector_thresholds():
    # Voice drift with small sample size
    voice_insuf = PilotDriftDetector.detect_voice_drift(
        baseline_stats={"intent_accuracy": 0.90},
        current_stats={"intent_accuracy": 0.60, "total_samples": 12},
        min_samples=30
    )
    assert voice_insuf["status"] == "INSUFFICIENT_SAMPLE_SIZE"

    # Task drift with adequate samples
    task_drift = PilotDriftDetector.detect_task_drift(
        baseline_stats={"median_completion_delay_days": 1.0, "postponement_rate": 0.10},
        current_stats={"median_completion_delay_days": 5.5, "postponement_rate": 0.40, "total_records": 40},
        min_samples=30
    )
    assert task_drift["drift_detected"] is True
    assert task_drift["status"] == "DRIFT_DETECTED"


# ============================================================================
# CATEGORY W & Z: MULTI-DIMENSIONAL ACCEPTANCE GATE & NO-FABRICATION
# ============================================================================
def test_multi_dimensional_acceptance_gate_not_production_ready():
    # When real field pilot data is absent, system must remain NOT_PRODUCTION_READY
    prod_gate = FieldValidationAcceptanceGate.evaluate_system_production_readiness(
        has_real_field_pilot_data=False
    )
    assert prod_gate["overall_status"] == "NOT_PRODUCTION_READY"
    assert prod_gate["is_production_ready"] is False
    assert prod_gate["real_field_pilot_data"] == "NOT_PRESENT"
    assert any("REAL_FIELD_PILOT_DATA = NOT_PRESENT" in r for r in prod_gate["blocking_reasons"])


# ============================================================================
# CATEGORY X: CROP-SPECIFIC FIELD STATUS
# ============================================================================
def test_crop_specific_field_status():
    tomato_status = FieldValidationAcceptanceGate.get_crop_field_status("tomato")
    assert tomato_status["status"] == "PILOT_DATA_PENDING"
    assert tomato_status["is_production_ready"] is False

    rice_status = FieldValidationAcceptanceGate.get_crop_field_status("rice")
    assert rice_status["status"] == "RESEARCH_ONLY"
    assert rice_status["is_production_ready"] is False


# ============================================================================
# CATEGORY Y: API SECURITY & ENDPOINTS
# ============================================================================
@pytest.mark.asyncio
async def test_pilot_api_security_and_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Unauthorized request should fail with 401
        res_unauth = await ac.get("/api/v1/pilot/status")
        assert res_unauth.status_code == 401

        # 2. Authorized request should succeed
        headers = {"Authorization": "Bearer test_auditor_token"}
        res_auth = await ac.get("/api/v1/pilot/status", headers=headers)
        assert res_auth.status_code == 200
        data = res_auth.json()
        assert data["field_pilot_status"] == "PILOT_DATA_PENDING"
        assert data["production_readiness"] == "NOT_PRODUCTION_READY"
        assert data["real_field_pilot_data"] == "NOT_PRESENT"
        assert data["rice_lock"] == "RESEARCH_ONLY"

        # 3. Crops endpoint
        res_crop = await ac.get("/api/v1/pilot/crops/rice", headers=headers)
        assert res_crop.status_code == 200
        assert res_crop.json()["status"] == "RESEARCH_ONLY"

        # 4. Acceptance endpoint
        res_acc = await ac.get("/api/v1/pilot/acceptance", headers=headers)
        assert res_acc.status_code == 200
        assert res_acc.json()["overall_status"] == "NOT_PRODUCTION_READY"


# ============================================================================
# SECTION 31: CRITICAL DATE/TIMEZONE HARDENING TEST
# ============================================================================
def test_task_postponement_timezone_preservation():
    """
    Ensures relative postponement preserves:
    - existing task due-time
    - farmer timezone
    - requested delay
    - date rollover
    Example: Friday 08:00:00+05:30 + 2 days = Sunday 08:00:00+05:30
    """
    farm_id = "farm_tz_test"
    TaskIntelligenceEngine.clear_tasks_for_farm(farm_id)

    original_due_iso = "2026-09-04T08:00:00+05:30"
    task = FarmTask(
        task_id="task_tz_1",
        farm_id=farm_id,
        crop="Tomato",
        task_type=TaskType.IRRIGATION,
        title="Morning Drip Irrigation",
        description="Run drip for 45 mins.",
        priority=DecisionPriority.HIGH,
        status=TaskStatus.DUE,
        due_at=original_due_iso,
        crop_stage="vegetative",
        trigger="schedule",
        reason="Preserve moisture",
        evidence="Tension meter",
        source_references=["FAO"],
        safety_status="VERIFIED_SAFE",
        trace_id="tr_tz"
    )
    TaskIntelligenceEngine._tasks_by_farm[farm_id] = [task]

    # Postpone by 2 days
    postponed_task = TaskIntelligenceEngine.postpone_task(
        task_id="task_tz_1",
        farmer_id="farmer_tz",
        days_to_postpone=2,
        reason="Field waterlogged after rain",
        farm_id=farm_id
    )

    assert postponed_task.status == TaskStatus.POSTPONED
    assert postponed_task.old_due_time == "2026-09-04T08:00:00+05:30"
    # Preserves 08:00:00 and +05:30 timezone offset, rolls date from 04 to 06!
    assert postponed_task.due_at == "2026-09-06T08:00:00+05:30"
    assert postponed_task.new_due_time == "2026-09-06T08:00:00+05:30"

    TaskIntelligenceEngine.clear_tasks_for_farm(farm_id)
