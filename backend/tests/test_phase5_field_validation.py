import os
import io
import pytest
from PIL import Image

from app.services.vision.field_validation.schemas import (
    FieldImageMetadata,
    ExpertLabelRecord,
    AnnotationState,
    ImageQualityAssessment,
    ModelFieldStatus,
    CropFieldEvaluationSummary
)
from app.services.vision.field_validation.validator import FieldDatasetValidator
from app.services.vision.field_validation.evaluator import FieldValidationEvaluator
from app.services.vision.field_validation.metrics import FieldMetricsCalculator
from app.services.vision.field_validation.domain_shift import DomainShiftAnalyzer
from app.services.vision.crop_registry import CropModelRegistry
from app.services.vision.quality_gate import ImageQualityGate
from app.services.safety.safety_engine import SafetyEngine


def create_test_leaf(color=(34, 139, 34), size=(256, 256)) -> bytes:
    from PIL import ImageDraw
    img = Image.new("RGB", size, color=color)
    if max(color) >= 20:
        draw = ImageDraw.Draw(img)
        for i in range(0, size[0], 8):
            draw.line([(i, 0), (i, size[1] - 1)], fill=(color[0] + 15, min(255, color[1] + 25), color[2] + 15), width=2)
            draw.line([(0, i), (size[0] - 1, i)], fill=(max(0, color[0] - 15), max(0, color[1] - 25), max(0, color[2] - 15)), width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# 1. Metadata Schema Validation
def test_metadata_schema_valid():
    valid_payload = {
        "image_id": "FLD_TOM_001",
        "crop": "tomato",
        "image_path": "images/tomato/FLD_TOM_001.jpg",
        "actual_disease": "early_blight",
        "location": "Lam Farm Guntur",
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
        "annotation_date": "2026-09-03",
        "farmer_id_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90"
    }
    is_valid, errors = FieldDatasetValidator.validate_metadata_record(valid_payload)
    assert is_valid is True
    assert len(errors) == 0


# 2. Missing Metadata Rejection
def test_missing_metadata_rejection():
    # Omitting camera_device and annotator_confidence
    invalid_payload = {
        "image_id": "FLD_TOM_002",
        "crop": "tomato",
        "image_path": "images/tomato/FLD_TOM_002.jpg",
        "actual_disease": "early_blight"
    }
    is_valid, errors = FieldDatasetValidator.validate_metadata_record(invalid_payload)
    assert is_valid is False
    assert len(errors) > 0


# 3. Invalid Crop Rejection
def test_invalid_crop_rejection():
    invalid_payload = {
        "image_id": "FLD_TOM_003",
        "crop": "dragonfruit",  # Unsupported crop
        "image_path": "images/dragonfruit/test.jpg",
        "actual_disease": "stem_canker",
        "location": "Madanapalle",
        "state": "Andhra Pradesh",
        "district": "Chittoor",
        "crop_stage": "vegetative",
        "lighting_condition": "direct_sunlight",
        "camera_device": "Samsung M02",
        "image_distance": "moderate_leaf_span",
        "leaf_condition": "fresh_attached",
        "occlusion_level": "none",
        "image_quality": "PASSED",
        "expert_label": "stem_canker",
        "annotator_confidence": 0.90,
        "annotation_source": "KVK",
        "annotation_date": "2026-09-03"
    }
    is_valid, errors = FieldDatasetValidator.validate_metadata_record(invalid_payload)
    assert is_valid is False
    assert any("Invalid crop" in e for e in errors)


# 4. Invalid Disease Label Rejection
def test_invalid_annotator_confidence_range():
    payload = {
        "image_id": "FLD_TOM_004",
        "crop": "tomato",
        "image_path": "images/tomato/FLD_TOM_004.jpg",
        "actual_disease": "early_blight",
        "location": "Guntur",
        "state": "Andhra Pradesh",
        "district": "Guntur",
        "crop_stage": "vegetative",
        "lighting_condition": "direct_sunlight",
        "camera_device": "Vivo Y20",
        "image_distance": "moderate_leaf_span",
        "leaf_condition": "fresh_attached",
        "occlusion_level": "none",
        "image_quality": "PASSED",
        "expert_label": "early_blight",
        "annotator_confidence": 1.50,  # Invalid: must be <= 1.0
        "annotation_source": "KVK",
        "annotation_date": "2026-09-03"
    }
    is_valid, errors = FieldDatasetValidator.validate_metadata_record(payload)
    assert is_valid is False


# 5. Duplicate Image Detection
def test_duplicate_image_detection(tmp_path):
    img1 = tmp_path / "img1.jpg"
    img2 = tmp_path / "img2.jpg"
    content = create_test_leaf()
    img1.write_bytes(content)
    img2.write_bytes(content)

    dups = FieldDatasetValidator.detect_duplicates([str(img1), str(img2)])
    assert len(dups) == 1
    assert len(list(dups.values())[0]) == 2


# 6. Cross-Split Leakage Detection
def test_cross_split_leakage_detection(tmp_path):
    # Benchmark folder fixture
    bench_dir = tmp_path / "benchmark"
    bench_dir.mkdir()
    b_file = bench_dir / "bench.jpg"
    leaf_bytes = create_test_leaf()
    b_file.write_bytes(leaf_bytes)

    # Compute hash of benchmark file
    b_hash = FieldDatasetValidator.compute_file_hash(str(b_file))

    # Field image with same hash must be flagged as leaked
    leaked = FieldDatasetValidator.check_cross_split_leakage([b_hash], benchmark_root=str(bench_dir))
    assert len(leaked) == 1
    assert leaked[0] == b_hash

    # Clean field hash
    clean_hash = "0123456789abcdef0123456789abcdef"
    clean = FieldDatasetValidator.check_cross_split_leakage([clean_hash], benchmark_root=str(bench_dir))
    assert len(clean) == 0


# 7. Blind Evaluation
def test_blind_evaluation():
    leaf_bytes = create_test_leaf()
    # Blind evaluator only accepts image_bytes and crop_hint
    pred, gate = FieldValidationEvaluator.evaluate_image_blind(leaf_bytes, crop="tomato")
    assert pred.crop == "tomato"
    assert hasattr(pred, "calibrated_confidence")
    assert hasattr(pred, "disease")
    # Verify model was not passed ground truth label
    assert not hasattr(pred, "expert_label")


# 8. ImageQualityGate Integration
def test_image_quality_gate_in_field_eval():
    dark_bytes = create_test_leaf(color=(5, 5, 5))
    pred, gate = FieldValidationEvaluator.evaluate_image_blind(dark_bytes, crop="tomato")
    assert gate.is_valid is False
    assert pred.quality_status == "FAILED"
    assert pred.is_reliable is False


# 9. Confidence Threshold Behavior
def test_confidence_threshold_buckets():
    mock_results = [
        {"confidence": 0.45, "is_correct": False},
        {"confidence": 0.60, "is_correct": True},
        {"confidence": 0.75, "is_correct": True},
        {"confidence": 0.92, "is_correct": True}
    ]
    buckets = FieldMetricsCalculator.calculate_confidence_buckets(mock_results)
    assert len(buckets) == 4
    assert buckets[0].bucket_range == "0.00-0.54"
    assert buckets[0].sample_count == 1
    assert buckets[0].accuracy == 0.0
    assert buckets[3].bucket_range == "0.85-1.00"
    assert buckets[3].sample_count == 1
    assert buckets[3].accuracy == 1.0


# 10. OOD Behavior
def test_ood_behavior():
    gray_bytes = create_test_leaf(color=(128, 128, 128))
    pred, _ = FieldValidationEvaluator.evaluate_image_blind(gray_bytes, crop="banana")
    assert pred.uncertainty_status in ["LOW", "MODERATE", "UNRELIABLE"]


# 11. Abstention Behavior
def test_abstention_behavior():
    mock_results = [
        {"quality_gate_status": True, "is_reliable": False, "is_ood": True, "confidence": 0.35, "annotation_state": "CONFIRMED", "expert_normalized": "a", "predicted_normalized": "b", "is_correct": False},
        {"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.90, "annotation_state": "CONFIRMED", "expert_normalized": "a", "predicted_normalized": "a", "is_correct": True}
    ]
    summary = FieldMetricsCalculator.calculate_crop_metrics("tomato", mock_results, 0.90, 0.90)
    assert summary.abstention_rate == 0.50
    assert summary.ood_rejection_rate == 0.50


# 12. Per-Class Metric Calculation
def test_per_class_metric_calculation():
    mock_results = [
        {"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.90, "annotation_state": "CONFIRMED", "expert_normalized": "early_blight", "predicted_normalized": "early_blight", "is_correct": True},
        {"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.88, "annotation_state": "CONFIRMED", "expert_normalized": "healthy", "predicted_normalized": "healthy", "is_correct": True}
    ]
    summary = FieldMetricsCalculator.calculate_crop_metrics("tomato", mock_results, 0.935, 0.9356)
    assert summary.accuracy == 1.0
    assert summary.macro_f1 == 1.0
    assert "early_blight" in summary.per_class_metrics
    assert "healthy" in summary.per_class_metrics


# 13. Benchmark-vs-Field Delta Calculation
def test_benchmark_vs_field_delta_calculation():
    mock_results = [
        {"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.85, "annotation_state": "CONFIRMED", "expert_normalized": "a", "predicted_normalized": "a", "is_correct": True},
        {"quality_gate_status": True, "is_reliable": True, "is_ood": False, "confidence": 0.80, "annotation_state": "CONFIRMED", "expert_normalized": "a", "predicted_normalized": "b", "is_correct": False}
    ]
    base = DomainShiftAnalyzer.get_benchmark_baseline("banana")
    summary = FieldMetricsCalculator.calculate_crop_metrics("banana", mock_results, benchmark_accuracy=base["accuracy"], benchmark_macro_f1=base["macro_f1"])
    shift = DomainShiftAnalyzer.compute_shift(summary)
    assert shift["has_field_data"] is True
    assert shift["delta_accuracy"] == round(0.50 - base["accuracy"], 4)


# 14. No-Field-Data Behavior
def test_no_field_data_behavior():
    summary = FieldMetricsCalculator.calculate_crop_metrics("tomato", [], benchmark_accuracy=0.935, benchmark_macro_f1=0.9356)
    assert summary.total_images == 0
    assert summary.field_validation_statement == "FIELD DATA NOT YET AVAILABLE"
    assert summary.current_status in [ModelFieldStatus.NOT_EVALUATED, ModelFieldStatus.FIELD_PENDING]

    shift = DomainShiftAnalyzer.compute_shift(summary)
    assert shift["has_field_data"] is False
    assert shift["field_accuracy"] is None
    assert shift["delta_accuracy"] is None


# 15. Rice Remains RESEARCH_ONLY
def test_rice_remains_research_only():
    base = DomainShiftAnalyzer.get_benchmark_baseline("rice")
    assert base["status"] == "RESEARCH_ONLY"

    summary = FieldMetricsCalculator.calculate_crop_metrics("rice", [], benchmark_accuracy=base["accuracy"], benchmark_macro_f1=base["macro_f1"])
    assert summary.current_status == ModelFieldStatus.RESEARCH_ONLY


# 16. SafetyEngine Remains Mandatory
def test_safety_engine_mandatory_in_field_context():
    res_banned = SafetyEngine.evaluate("Apply Monocrotophos 36% SL on field tomato leaves.", crop="tomato")
    assert res_banned.is_safe is False
    assert len(res_banned.blocked_reasons) > 0

    res_safe = SafetyEngine.evaluate("Apply Mancozeb 75% WP @ 2.5g/L with gloves.", crop="tomato")
    assert res_safe.is_safe is True
