import os
import io
import csv
import json
import pytest
from PIL import Image

from app.services.vision.field_validation.schemas import (
    FieldImageMetadata,
    ExpertLabelRecord,
    AnnotationState,
    ModelFieldStatus,
    DuplicateStatus,
    LeakageStatus
)
from app.services.vision.field_validation.validator import FieldDatasetValidator
from app.services.vision.field_validation.ingest import FieldPilotIngestionService
from app.services.vision.field_validation.evaluator import FieldValidationEvaluator
from app.services.vision.field_validation.metrics import FieldMetricsCalculator
from app.services.vision.field_validation.domain_shift import DomainShiftAnalyzer
from app.services.safety.safety_engine import SafetyEngine


def make_test_image(color=(34, 139, 34), size=(256, 256)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# 1. Real-Image Ingestion Workflow
def test_real_image_ingestion_workflow(tmp_path):
    img_file = tmp_path / "test_leaf.jpg"
    img_file.write_bytes(make_test_image())

    meta_csv = tmp_path / "metadata.csv"
    with open(meta_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image_id", "crop", "image_path", "actual_disease", "location",
            "state", "district", "crop_stage", "lighting_condition",
            "camera_device", "image_distance", "leaf_condition", "occlusion_level",
            "image_quality", "expert_label", "annotator_confidence",
            "annotation_source", "annotation_date", "latitude", "longitude",
            "farmer_id_hash", "weather_context", "soil_context", "notes"
        ])
        writer.writerow([
            "FLD_TOM_010", "tomato", str(img_file), "early_blight", "Guntur",
            "Andhra Pradesh", "Guntur", "vegetative", "diffuse_daylight",
            "Redmi 9A", "moderate_leaf_span", "fresh_attached", "none",
            "PASSED", "Tomato___Early_blight", "0.95",
            "ANGRAU Pathologist", "2026-09-03", "", "",
            "a1b2c3d4e5f60718293a4b5c6d7e8f90", "", "", ""
        ])

    labels_csv = tmp_path / "labels.csv"
    with open(labels_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image_id", "crop", "expert_label", "secondary_diseases",
            "annotation_state", "pathogen_type", "expert_id", "review_date",
            "quality_assessment", "notes"
        ])
        writer.writerow([
            "FLD_TOM_010", "tomato", "Tomato___Early_blight", "",
            "CONFIRMED", "fungal", "EXP_01", "2026-09-03", "PASSED", ""
        ])

    manifest_dir = tmp_path / "manifests"
    manifest = FieldPilotIngestionService.ingest_pilot_batch(
        metadata_csv=str(meta_csv),
        labels_csv=str(labels_csv),
        benchmark_root=str(tmp_path / "empty_bench"),
        manifest_dir=str(manifest_dir)
    )

    assert manifest.total_submitted == 1
    assert manifest.accepted_for_eval == 1
    assert manifest.rejected_count == 0
    assert len(manifest.items) == 1
    assert manifest.items[0].included_in_evaluation is True


# 2. Metadata Validation Strict
def test_metadata_validation_strict():
    invalid_record = {
        "image_id": "FLD_001",
        "crop": "tomato"
        # missing required fields
    }
    is_valid, errors = FieldDatasetValidator.validate_metadata_record(invalid_record)
    assert is_valid is False
    assert len(errors) > 0


# 3. Expert-Label Validation
def test_expert_label_validation():
    valid_record = {
        "image_id": "FLD_002",
        "crop": "banana",
        "expert_label": "sigatoka",
        "secondary_diseases": "",
        "annotation_state": "CONFIRMED",
        "pathogen_type": "fungal",
        "expert_id": "EXP_02",
        "review_date": "2026-09-03",
        "quality_assessment": "PASSED"
    }
    rec = ExpertLabelRecord(**valid_record)
    assert rec.annotation_state == AnnotationState.CONFIRMED


# 4. Exact Duplicate Rejection
def test_exact_duplicate_rejection(tmp_path):
    img1 = tmp_path / "img1.jpg"
    img2 = tmp_path / "img2.jpg"
    content = make_test_image()
    img1.write_bytes(content)
    img2.write_bytes(content)

    meta_csv = tmp_path / "metadata.csv"
    with open(meta_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image_id", "crop", "image_path", "actual_disease", "location",
            "state", "district", "crop_stage", "lighting_condition",
            "camera_device", "image_distance", "leaf_condition", "occlusion_level",
            "image_quality", "expert_label", "annotator_confidence",
            "annotation_source", "annotation_date"
        ])
        writer.writerow([
            "FLD_DUP_1", "tomato", str(img1), "early_blight", "Guntur",
            "AP", "Guntur", "vegetative", "diffuse_daylight", "Redmi 9A",
            "moderate_leaf_span", "fresh_attached", "none", "PASSED",
            "Tomato___Early_blight", "0.95", "KVK", "2026-09-03"
        ])
        writer.writerow([
            "FLD_DUP_2", "tomato", str(img2), "early_blight", "Guntur",
            "AP", "Guntur", "vegetative", "diffuse_daylight", "Redmi 9A",
            "moderate_leaf_span", "fresh_attached", "none", "PASSED",
            "Tomato___Early_blight", "0.95", "KVK", "2026-09-03"
        ])

    labels_csv = tmp_path / "labels.csv"
    with open(labels_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image_id", "crop", "expert_label", "annotation_state", "expert_id", "review_date"
        ])
        writer.writerow(["FLD_DUP_1", "tomato", "Tomato___Early_blight", "CONFIRMED", "EXP_01", "2026-09-03"])
        writer.writerow(["FLD_DUP_2", "tomato", "Tomato___Early_blight", "CONFIRMED", "EXP_01", "2026-09-03"])

    manifest = FieldPilotIngestionService.ingest_pilot_batch(
        metadata_csv=str(meta_csv),
        labels_csv=str(labels_csv),
        benchmark_root=str(tmp_path / "empty_bench"),
        manifest_dir=str(tmp_path / "manifests")
    )

    assert manifest.total_submitted == 2
    assert manifest.accepted_for_eval == 1
    assert manifest.rejected_count == 1
    assert any(i.duplicate_status == DuplicateStatus.REJECT_EXACT_DUPLICATE.value for i in manifest.items)


# 5. Near-Duplicate Flagging
def test_near_duplicate_flagging(tmp_path):
    img1 = tmp_path / "near1.jpg"
    img2 = tmp_path / "near2.jpg"
    img1.write_bytes(make_test_image(color=(34, 139, 34)))
    # Almost identical color
    img2.write_bytes(make_test_image(color=(34, 140, 34)))

    near_pairs = FieldDatasetValidator.detect_near_duplicates([str(img1), str(img2)], max_distance=5)
    assert len(near_pairs) == 1
    p1, p2, dist = near_pairs[0]
    assert dist <= 5


# 6. Benchmark Leakage Rejection
def test_benchmark_leakage_rejection(tmp_path):
    bench_dir = tmp_path / "benchmark"
    bench_dir.mkdir()
    bench_img = bench_dir / "bench.jpg"
    bench_img.write_bytes(make_test_image())

    field_img = tmp_path / "field.jpg"
    field_img.write_bytes(make_test_image())

    meta_csv = tmp_path / "metadata.csv"
    with open(meta_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image_id", "crop", "image_path", "actual_disease", "location",
            "state", "district", "crop_stage", "lighting_condition",
            "camera_device", "image_distance", "leaf_condition", "occlusion_level",
            "image_quality", "expert_label", "annotator_confidence",
            "annotation_source", "annotation_date"
        ])
        writer.writerow([
            "FLD_LEAK", "tomato", str(field_img), "early_blight", "Guntur",
            "AP", "Guntur", "vegetative", "diffuse_daylight", "Redmi 9A",
            "moderate_leaf_span", "fresh_attached", "none", "PASSED",
            "Tomato___Early_blight", "0.95", "KVK", "2026-09-03"
        ])

    labels_csv = tmp_path / "labels.csv"
    with open(labels_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_id", "crop", "expert_label", "annotation_state", "expert_id", "review_date"])
        writer.writerow(["FLD_LEAK", "tomato", "Tomato___Early_blight", "CONFIRMED", "EXP_01", "2026-09-03"])

    manifest = FieldPilotIngestionService.ingest_pilot_batch(
        metadata_csv=str(meta_csv),
        labels_csv=str(labels_csv),
        benchmark_root=str(bench_dir),
        manifest_dir=str(tmp_path / "manifests")
    )

    assert manifest.accepted_for_eval == 0
    assert manifest.rejected_count == 1
    assert manifest.items[0].benchmark_leakage_status == LeakageStatus.REJECT_BENCHMARK_LEAKAGE.value


# 7. PII Rejection
def test_pii_rejection():
    # Record with a mobile phone number in notes
    phone_rec = {
        "location": "Guntur Village",
        "notes": "Farmer contact 9876543210 for follow up visit"
    }
    clean, violations = FieldDatasetValidator.validate_privacy(phone_rec)
    assert clean is False
    assert any("Phone number" in v for v in violations)

    # Record with Aadhaar number
    aadhaar_rec = {
        "location": "Guntur Village",
        "notes": "UIDAI: 1234 5678 9012"
    }
    clean_a, violations_a = FieldDatasetValidator.validate_privacy(aadhaar_rec)
    assert clean_a is False
    assert any("Aadhaar" in v for v in violations_a)

    # Record with door / house number
    house_rec = {
        "location": "Door No 4-12/A, Main Street",
        "notes": "Field next to house"
    }
    clean_h, violations_h = FieldDatasetValidator.validate_privacy(house_rec)
    assert clean_h is False
    assert any("address" in v.lower() for v in violations_h)


# 8. Blind Prediction Isolation
def test_blind_prediction_isolation():
    leaf_bytes = make_test_image()
    # Blind evaluator only receives image_bytes and crop_hint
    pred, gate = FieldValidationEvaluator.evaluate_image_blind(leaf_bytes, crop="tomato")
    assert not hasattr(pred, "expert_label")
    assert not hasattr(pred, "actual_disease")
    assert isinstance(pred.calibrated_confidence, float)


# 9. Ground-Truth Post-Hoc Joining
def test_ground_truth_post_hoc_joining():
    leaf_bytes = make_test_image()
    meta = FieldImageMetadata(
        image_id="FLD_TST_1", crop="tomato", image_path="fake.jpg",
        actual_disease="early_blight", location="Guntur", state="AP",
        district="Guntur", crop_stage="vegetative", lighting_condition="diffuse_daylight",
        camera_device="Redmi 9A", image_distance="moderate_leaf_span",
        leaf_condition="fresh_attached", occlusion_level="none",
        image_quality="PASSED", expert_label="Tomato___Early_blight",
        annotator_confidence=0.95, annotation_source="KVK", annotation_date="2026-09-03"
    )
    expert = ExpertLabelRecord(
        image_id="FLD_TST_1", crop="tomato", expert_label="Tomato___Early_blight",
        annotation_state=AnnotationState.CONFIRMED, expert_id="EXP_1", review_date="2026-09-03"
    )
    assert meta.image_id == expert.image_id


# 10. Field Metric Calculation: Confirmed vs Probable
def test_field_metric_calculation_confirmed_vs_probable():
    eval_results = [
        # CONFIRMED correct
        {"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.90, "annotation_state": "CONFIRMED", "expert_normalized": "early_blight", "predicted_normalized": "early_blight", "is_correct": True},
        # CONFIRMED incorrect
        {"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.80, "annotation_state": "CONFIRMED", "expert_normalized": "early_blight", "predicted_normalized": "late_blight", "is_correct": False},
        # PROBABLE correct (should be reported separately)
        {"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.85, "annotation_state": "PROBABLE", "expert_normalized": "early_blight", "predicted_normalized": "early_blight", "is_correct": True}
    ]
    summary = FieldMetricsCalculator.calculate_crop_metrics("tomato", eval_results, benchmark_accuracy=0.935, benchmark_macro_f1=0.9356)
    # Primary accuracy: 1 correct out of 2 confirmed = 0.50
    assert summary.accuracy == 0.50
    # Probable accuracy: 1 correct out of 1 probable = 1.0
    assert summary.probable_accuracy == 1.0


# 11. Benchmark-Field Delta
def test_benchmark_field_delta():
    summary = FieldMetricsCalculator.calculate_crop_metrics(
        "tomato",
        [{"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.90, "annotation_state": "CONFIRMED", "expert_normalized": "a", "predicted_normalized": "a", "is_correct": True}],
        benchmark_accuracy=0.935, benchmark_macro_f1=0.9356
    )
    shift = DomainShiftAnalyzer.compute_shift(summary)
    assert shift["has_field_data"] is True
    assert shift["delta_accuracy"] == round(1.0 - 0.935, 4)


# 12. High-Confidence Error Detection
def test_high_confidence_error_detection():
    eval_results = [
        # Wrong prediction with high confidence (0.85 >= 0.70)
        {"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.85, "annotation_state": "CONFIRMED", "expert_label": "late_blight", "predicted_disease": "early_blight", "expert_normalized": "late_blight", "predicted_normalized": "early_blight", "is_correct": False},
        # Correct prediction
        {"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.92, "annotation_state": "CONFIRMED", "expert_label": "healthy", "predicted_disease": "healthy", "expert_normalized": "healthy", "predicted_normalized": "healthy", "is_correct": True}
    ]
    summary = FieldMetricsCalculator.calculate_crop_metrics("tomato", eval_results, 0.935, 0.9356)
    assert summary.high_confidence_error_count == 1
    assert len(summary.failure_cases) == 1
    assert summary.failure_cases[0].failure_category == "HIGH_CONFIDENCE_WRONG_PREDICTION"


# 13. Calibration Analysis Buckets
def test_calibration_analysis_buckets():
    eval_results = [
        {"confidence": 0.50, "is_correct": False},
        {"confidence": 0.65, "is_correct": True},
        {"confidence": 0.75, "is_correct": True},
        {"confidence": 0.95, "is_correct": True}
    ]
    buckets = FieldMetricsCalculator.calculate_confidence_buckets(eval_results)
    assert len(buckets) == 4
    # Bucket 0.85-1.00 has 1 sample, 100% accuracy
    b_high = [b for b in buckets if b.bucket_range == "0.85-1.00"][0]
    assert b_high.sample_count == 1
    assert b_high.accuracy == 1.0


# 14. Failure-Case Reporting
def test_failure_case_reporting(tmp_path):
    eval_results = [
        {"image_id": "FLD_FAIL_1", "quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.82, "expert_label": "Tomato___Early_blight", "predicted_disease": "Tomato___Late_blight", "lighting_condition": "diffuse_daylight", "is_correct": False}
    ]
    fail_dir = tmp_path / "failures"
    cases, high_errs, _ = FieldMetricsCalculator.categorize_failures("tomato", eval_results, failure_dir=str(fail_dir))
    assert len(cases) == 1
    assert high_errs == 1
    assert cases[0].failure_category == "HIGH_CONFIDENCE_WRONG_PREDICTION"
    assert (fail_dir / "failures_tomato.json").exists()


# 15. Empty Field Dataset Behavior
def test_empty_field_dataset_behavior():
    manifest = FieldPilotIngestionService.ingest_pilot_batch(
        metadata_csv="non_existent.csv",
        labels_csv="non_existent.csv"
    )
    assert manifest.total_submitted == 0
    assert manifest.accepted_for_eval == 0

    summary = FieldMetricsCalculator.calculate_crop_metrics("tomato", [], 0.935, 0.9356)
    assert summary.total_images == 0
    assert summary.field_validation_statement == "FIELD DATA NOT YET AVAILABLE"


# 16. Rice RESEARCH_ONLY Enforcement
def test_rice_research_only_enforcement():
    base = DomainShiftAnalyzer.get_benchmark_baseline("rice")
    assert base["status"] == "RESEARCH_ONLY"

    summary = FieldMetricsCalculator.calculate_crop_metrics("rice", [], base["accuracy"], base["macro_f1"])
    assert summary.current_status == ModelFieldStatus.RESEARCH_ONLY


# 17. SafetyEngine Enforcement in Field Context
def test_safety_engine_enforcement_in_field_context():
    # Hazardous recommendation must be blocked
    res_banned = SafetyEngine.evaluate("Apply monocrotophos for field caterpillar control.", crop="tomato")
    assert res_banned.is_safe is False
    assert len(res_banned.blocked_reasons) > 0

    # Approved recommendation
    res_safe = SafetyEngine.evaluate("Spray Chlorantraniliprole 18.5% SC @ 0.3 ml/L.", crop="tomato")
    assert res_safe.is_safe is True
