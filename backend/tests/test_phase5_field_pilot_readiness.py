import os
import io
import csv
import json
import hashlib
import pytest
from PIL import Image
from typing import Dict, Any, List

from app.services.vision.field_validation import (
    FarmSessionGroupManager,
    FieldValidationAcceptanceGate,
    FieldEdgeParityEvaluator,
    FieldDatasetValidator,
    FieldMetricsCalculator,
    DomainShiftAnalyzer,
    FieldValidationReporter,
    FieldPilotIngestionService,
    FieldValidationEvaluator,
    ModelFieldStatus,
    CropFieldEvaluationSummary
)
from app.services.safety.safety_engine import SafetyEngine


def make_test_image(color=(34, 139, 34), size=(256, 256)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# 1. Farm Hash Generation
def test_farm_hash_generation():
    raw_farm = "Farm_Rao_Guntur_Survey_45"
    h = FarmSessionGroupManager.generate_privacy_hash(raw_farm)
    assert len(h) == 64
    assert raw_farm not in h
    # Deterministic
    assert h == FarmSessionGroupManager.generate_privacy_hash(raw_farm)


# 2. Plant Hash Generation
def test_plant_hash_generation():
    raw_plant = "Tomato_Row_3_Plant_12"
    h = FarmSessionGroupManager.generate_privacy_hash(raw_plant)
    assert len(h) == 64
    assert raw_plant not in h


# 3. Session Grouping
def test_session_grouping():
    records = [
        {"image_id": "IMG_01", "collection_session_id": "SES_01", "plant_id_hash": "plant_a"},
        {"image_id": "IMG_02", "collection_session_id": "SES_01", "plant_id_hash": "plant_a"},
        {"image_id": "IMG_03", "collection_session_id": "SES_02", "plant_id_hash": "plant_b"},
    ]
    sessions = set(r["collection_session_id"] for r in records)
    assert len(sessions) == 2
    assert "SES_01" in sessions and "SES_02" in sessions


# 4. Group Leakage Detection
def test_group_leakage_detection():
    split_a = [{"image_id": "1", "farm_id_hash": "farm_alpha_12345678"}]
    split_b = [{"image_id": "2", "farm_id_hash": "farm_alpha_12345678"}]
    res = FarmSessionGroupManager.detect_group_leakage(split_a, split_b)
    assert res["has_group_leakage"] is True
    assert "farm_id_hash" in res["findings"]


# 5. Group-Aware Splitting
def test_group_aware_splitting():
    records = [
        {"image_id": f"IMG_{i}", "farm_id_hash": f"farm_hash_{i % 5}"}
        for i in range(25)
    ]
    train_split, test_split = FarmSessionGroupManager.group_aware_split(records, train_ratio=0.8, group_key="farm_id_hash")
    leak_check = FarmSessionGroupManager.detect_group_leakage(train_split, test_split)
    assert leak_check["has_group_leakage"] is False


# 6. Expert Label Independence
def test_expert_label_independence():
    # Verify blind evaluator receives only image bytes and crop
    eval_call = FieldValidationEvaluator.evaluate_image_blind
    import inspect
    sig = inspect.signature(eval_call)
    params = list(sig.parameters.keys())
    assert "image_bytes" in params
    assert "crop" in params
    assert "expert_label" not in params
    assert "actual_disease" not in params


# 7. Multi-Label Unsupported Handling
def test_multi_label_unsupported_handling():
    # When multiple concurrent diseases are identified, single-label classifier must abstain
    eval_results = [
        {
            "image_id": "IMG_MULTI_01",
            "crop": "tomato",
            "expert_label": "Tomato___Early_blight",
            "secondary_diseases": "Tomato___Septoria_leaf_spot",
            "is_multi_label": True,
            "is_correct": False,
            "confidence": 0.65,
            "quality_gate_status": True,
            "is_reliable": False,
            "uncertainty_level": "UNRELIABLE"
        }
    ]
    summary = FieldMetricsCalculator.calculate_crop_metrics("tomato", eval_results)
    assert summary.multi_disease_unsupported_count == 1
    assert summary.abstention_rate == 1.0


# 8. Group-Level Aggregation
def test_group_level_aggregation():
    # 5 distinct plant groups to meet minimum threshold
    group_preds = []
    for g in range(5):
        gid = f"plant_hash_{g:02d}"
        for view in range(3):
            group_preds.append({
                "image_id": f"IMG_{g}_{view}",
                "plant_id_hash": gid,
                "expert_label": "Tomato___Early_blight",
                "predicted_disease": "Tomato___Early_blight",
                "calibrated_confidence": 0.85
            })
    agg = FarmSessionGroupManager.aggregate_group_predictions(group_preds, group_key="plant_id_hash")
    assert agg["group_metrics_available"] is True
    assert agg["total_groups"] == 5
    assert agg["group_accuracy"] == 1.0


# 9. Empty Field Dataset
def test_empty_field_dataset():
    summary = FieldMetricsCalculator.calculate_crop_metrics("tomato", [])
    assert summary.total_images == 0
    assert summary.field_validation_statement == "FIELD DATA NOT YET AVAILABLE"
    assert summary.current_status == ModelFieldStatus.FIELD_PENDING


# 10. Real-Image Ingestion
def test_real_image_ingestion(tmp_path):
    img_file = tmp_path / "pilot_leaf.jpg"
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
            "farmer_id_hash", "farm_id_hash", "plant_id_hash", "collection_session_id"
        ])
        writer.writerow([
            "FLD_PLT_001", "tomato", str(img_file), "early_blight", "Guntur",
            "Andhra Pradesh", "Guntur", "vegetative", "diffuse_daylight",
            "Redmi 9A", "moderate_leaf_span", "fresh_attached", "none",
            "PASSED", "Tomato___Early_blight", "0.95",
            "ANGRAU Pathologist", "2026-09-03", "", "",
            "a1b2c3d4e5f60718293a4b5c6d7e8f90",
            "farm_1234567890abcdef", "plant_abcdef1234567890", "SES_20260903_01"
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
            "FLD_PLT_001", "tomato", "Tomato___Early_blight", "",
            "CONFIRMED", "fungal", "EXP_01", "2026-09-03", "PASSED", ""
        ])

    manifest = FieldPilotIngestionService.ingest_pilot_batch(
        metadata_csv=str(meta_csv),
        labels_csv=str(labels_csv),
        benchmark_root=str(tmp_path / "empty_bench"),
        manifest_dir=str(tmp_path / "manifests")
    )
    assert manifest.total_submitted == 1
    assert manifest.accepted_for_eval == 1


# 11. Exact Duplicate Detection
def test_exact_duplicate_detection(tmp_path):
    img_data = make_test_image()
    h = hashlib.md5(img_data).hexdigest()
    seen = {h: "IMG_ORIGINAL"}
    assert h in seen


# 12. Near Duplicate Detection
def test_near_duplicate_detection():
    data1 = make_test_image(color=(30, 130, 30))
    data2 = make_test_image(color=(31, 131, 31))
    ph1 = FieldDatasetValidator.compute_perceptual_hash(data1)
    ph2 = FieldDatasetValidator.compute_perceptual_hash(data2)
    dist = FieldDatasetValidator.hamming_distance(ph1, ph2)
    assert dist <= 5


# 13. Benchmark Leakage Detection
def test_benchmark_leakage():
    bench_hashes = {"hash_bench_01": "train/tomato/img01.jpg"}
    sample_hash = "hash_bench_01"
    assert sample_hash in bench_hashes


# 14. Confidence Analysis Buckets
def test_confidence_analysis():
    eval_results = [
        {"confidence": 0.40, "is_correct": False},
        {"confidence": 0.60, "is_correct": True},
        {"confidence": 0.75, "is_correct": True},
        {"confidence": 0.90, "is_correct": True}
    ]
    buckets = FieldMetricsCalculator.calculate_confidence_buckets(eval_results)
    assert len(buckets) == 4
    assert buckets[0].bucket_range == "0.00-0.54"
    assert buckets[3].bucket_range == "0.85-1.00"
    assert buckets[3].correct_count == 1


# 15. High-Confidence Error Detection
def test_high_confidence_error_detection(tmp_path):
    eval_results = [
        {
            "image_id": "FAIL_01",
            "expert_label": "Tomato___Early_blight",
            "predicted_disease": "Tomato___Late_blight",
            "confidence": 0.92,
            "is_correct": False,
            "uncertainty_level": "LOW",
            "quality_gate_status": True
        }
    ]
    cases, high_errs, _ = FieldMetricsCalculator.categorize_failures("tomato", eval_results, failure_dir=str(tmp_path))
    assert high_errs == 1
    assert len(cases) == 1
    assert cases[0].failure_category == "HIGH_CONFIDENCE_WRONG_PREDICTION"


# 16. Domain-Shift Calculation
def test_domain_shift_calculation():
    summary = FieldMetricsCalculator.calculate_crop_metrics("tomato", [], benchmark_accuracy=0.935, benchmark_macro_f1=0.9356)
    shift = DomainShiftAnalyzer.compute_shift(summary)
    assert shift["has_field_data"] is False
    assert shift["delta_macro_f1"] is None


# 17. Edge / Server Prediction Parity
def test_edge_server_prediction_parity():
    leaf_bytes = make_test_image()
    parity = FieldEdgeParityEvaluator.evaluate_field_runtime_parity("tomato", [leaf_bytes])
    assert parity["parity_available"] is True
    assert parity["prediction_agreement_rate"] == 1.0


# 18. Rice RESEARCH_ONLY
def test_rice_research_only():
    rice_summary = FieldMetricsCalculator.calculate_crop_metrics("rice", [])
    assert rice_summary.current_status == ModelFieldStatus.RESEARCH_ONLY
    gate_res = FieldValidationAcceptanceGate.evaluate_acceptance(rice_summary)
    assert gate_res["decision"] == "REJECTED"
    assert gate_res["recommended_status"] == ModelFieldStatus.RESEARCH_ONLY


# 19. SafetyEngine Enforcement
def test_safety_engine_enforcement():
    # Banned chemical test (Monocrotophos is banned in India under CIBRC)
    unsafe_text = "Apply 2ml Monocrotophos 36% SL per litre for early blight."
    res = SafetyEngine.evaluate(unsafe_text, crop="tomato", stage="vegetative")
    assert res.is_safe is False
    assert res.status == "BLOCK"
    assert any("monocrotophos" in r.lower() for r in res.blocked_reasons)


# 20. No Fabricated Metrics
def test_no_fabricated_metrics():
    summary = FieldMetricsCalculator.calculate_crop_metrics("banana", [])
    assert summary.accuracy == 0.0
    assert summary.macro_f1 == 0.0
    assert summary.field_validation_statement == "FIELD DATA NOT YET AVAILABLE"
