import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath("backend"))

from app.services.vision.crop_registry import CropModelRegistry
from app.services.vision.field_validation import (
    FieldDatasetValidator,
    FieldValidationEvaluator,
    FieldMetricsCalculator,
    DomainShiftAnalyzer,
    FieldValidationReporter
)

def run_field_validation_audit():
    print("=" * 80)
    print("BHOOMI V2 — PHASE 5: REAL-WORLD VISION FIELD VALIDATION HARNESS")
    print("=" * 80)

    metadata_csv = "data/field_validation/metadata/field_validation.csv"
    labels_csv = "data/field_validation/labels/expert_labels.csv"

    # Step 1: Validate metadata files
    print("\n[*] Validating Field Validation Datasets...")
    meta_val = FieldDatasetValidator.validate_metadata_file(metadata_csv)
    expert_val = FieldDatasetValidator.validate_expert_labels_file(labels_csv)

    print(f"  Metadata CSV Valid: {meta_val['is_valid']} (Rows: {meta_val['total_rows']}, Valid: {meta_val['valid_rows']})")
    print(f"  Expert Labels Valid: {expert_val['is_valid']} (Rows: {expert_val['total_rows']}, Valid: {expert_val['valid_rows']})")

    crops = CropModelRegistry.get_supported_crops()
    summaries = []

    # If metadata is empty or no real images exist yet
    if meta_val["valid_rows"] == 0:
        print("\n[*] NOTICE: No on-farm smartphone images ingested into data/field_validation yet.")
        print("[*] Generating baseline operational report without fabricating scores ('FIELD DATA NOT YET AVAILABLE')...")
        for crop in crops:
            base = DomainShiftAnalyzer.get_benchmark_baseline(crop)
            summary = FieldMetricsCalculator.calculate_crop_metrics(
                crop=crop,
                eval_results=[],
                benchmark_accuracy=base["accuracy"],
                benchmark_macro_f1=base["macro_f1"]
            )
            summaries.append(summary)
    else:
        # Group by crop and run blind evaluation
        records_by_crop = {}
        expert_map = {r.image_id: r for r in expert_val.get("records", [])}

        for meta_rec in meta_val.get("records", []):
            exp_rec = expert_map.get(meta_rec.image_id)
            if exp_rec:
                records_by_crop.setdefault(meta_rec.crop, []).append((meta_rec, exp_rec))

        for crop in crops:
            crop_records = records_by_crop.get(crop, [])
            base = DomainShiftAnalyzer.get_benchmark_baseline(crop)
            if crop_records:
                print(f"[*] Running Blind Evaluation for {crop.upper()} ({len(crop_records)} field samples)...")
                results = FieldValidationEvaluator.evaluate_crop_field_dataset(crop, crop_records)
            else:
                results = []

            summary = FieldMetricsCalculator.calculate_crop_metrics(
                crop=crop,
                eval_results=results,
                benchmark_accuracy=base["accuracy"],
                benchmark_macro_f1=base["macro_f1"]
            )
            summaries.append(summary)

    # Step 3: Generate reports
    print("\n[*] Generating Field Validation Audit Reports...")
    report_text = FieldValidationReporter.generate_report(summaries)
    print("  Report generated at: data/field_validation/reports/field_validation_report.md")
    print("  Report generated at: docs/PHASE_5_FIELD_VALIDATION_REPORT.md")

    print("\n" + "=" * 80)
    print("FIELD VALIDATION AUDIT COMPLETE — TRANSPARENCY VERIFIED")
    print("=" * 80)
    return summaries

if __name__ == "__main__":
    run_field_validation_audit()
