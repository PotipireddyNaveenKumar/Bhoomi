# BHOOMI V2 — Phase 5 Real-World Vision Field Validation Report

**Audit Execution Timestamp**: 2026-09-03 21:06:22  
**Pipeline Harness Version**: `field_validation_v3.0_pilot_intake`  
**Overall Field Data State**: **FIELD DATA NOT YET AVAILABLE**  

---

## 1. Pilot Dataset Overview

> [!IMPORTANT]
> **FIELD DATA TRANSPARENCY NOTICE**: No real-world on-farm smartphone images have been submitted or ingested yet into `data/field_validation/images/`. In accordance with BHOOMI safety guidelines, **NO FAKE METRICS ARE FABRICATED**. The target pilot dataset is 50 real confirmed smartphone images per crop (minimum 30 confirmed) across Tomato, Banana, Guava, and Corn/Maize (Total target: 200 field images).

## 2. Crop Distribution

- Tomato: **0 field images** (Target: 50, Min: 30)
- Banana: **0 field images** (Target: 50, Min: 30)
- Guava: **0 field images** (Target: 50, Min: 30)
- Corn/Maize: **0 field images** (Target: 50, Min: 30)
- Rice: **0 field images** (`RESEARCH_ONLY` — permanently barred from farmer diagnosis)

## 3. Farm Distribution & Diversity

Independent Farms: **0 registered**. (Requirement: $\ge 5$ independent agricultural farm locations per crop with one-way SHA-256 `farm_id_hash` anonymization).

## 4. Device Distribution & Diversity

Camera Devices Logged: **0**. Protocol requires testing across low-end sensors (e.g. Redmi 9A/Realme C-series) and mid/high-end smartphones.

## 5. Collection Session Distribution

Collection Sessions: **0 registered**. Sessions tracked via `collection_session_id` to monitor lighting and time-of-day diversity.

## 6. Expert Label Distribution

Ground truth is established by independent plant pathologists prior to BHOOMI blind inference. Labels are categorized into `CONFIRMED`, `PROBABLE`, `UNCERTAIN`, and `UNKNOWN`.
- Confirmed Labels: **0**
- Probable Labels: **0**
- Uncertain / Unknown: **0**

## 7. Duplicate Analysis

- Exact Duplicates: **0 detected** (MD5 hash verification)
- Near Duplicates: **0 flagged** (Perceptual aHash Hamming distance $\le 5$ bits)

## 8. Leakage Analysis & Group Integrity

- Benchmark Cross-Leakage: **0 matches** (Checked against training, validation, and benchmark test sets)
- Cross-Split Group Leakage: **0 matches** (Verified via `FarmSessionGroupManager`)

## 9. Image-Quality Analysis

Quality Gate Status: Ready. Filters for blur, extreme darkness ($<30/255$), extreme overexposure ($>245/255$), and minimum resolution ($224\times224$).

## 10. Image-Level Primary Metrics (CONFIRMED Labels Only)

> **FIELD DATA NOT YET AVAILABLE**: Accuracy, Precision, Recall, Macro-F1, and Confusion Matrices will be calculated once verified field images are ingested.

## 11. Group-Level Metrics

> **GROUP-LEVEL METRICS NOT YET RELIABLE**: Aggregated plant-level metrics will be computed using Confidence-Weighted Soft Voting once $\ge 5$ plant groups are available.

## 12. Confidence Distribution & Calibration Analysis

Model confidence is evaluated across 4 standard buckets: `0.00-0.54`, `0.55-0.69`, `0.70-0.84`, and `0.85-1.00`. Calibrated confidence uses post-hoc temperature scaling ($T$).

## 13. Out-of-Distribution (OOD) & Abstention Analysis

Non-leaf images, background soil/weeds, and low-confidence foliar patterns trigger abstention via `VisionPredictionValidator`, preventing hazardous overconfident misdiagnoses.

## 14. High-Confidence Failures (Safety Critical)

High-confidence errors (calibrated confidence $\ge 0.85$ with incorrect prediction) are tracked as safety blockers. Safety limit: $\le 5\%$ error rate.

## 15. Structured Failure Case Records

Failure records are archived to `data/field_validation/reports/failure_cases/failures_<crop>.json` categorizing failures by lighting, blur, occlusion, disease similarity, and multi-label symptoms.

## 16. Benchmark-vs-Field Comparison

| Crop | Benchmark Accuracy | Benchmark Macro-F1 | Field Accuracy | Field Macro-F1 | Delta Accuracy | Delta Macro-F1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Tomato** | 93.5% | 93.6% | N/A | N/A | N/A | N/A |
| **Chilli** | 78.0% | 78.5% | N/A | N/A | N/A | N/A |
| **Rice** | 36.5% | 35.2% | N/A | N/A | N/A | N/A |
| **Potato** | 68.9% | 66.8% | N/A | N/A | N/A | N/A |
| **Sugarcane** | 73.0% | 73.0% | N/A | N/A | N/A | N/A |
| **Banana** | 92.4% | 92.6% | N/A | N/A | N/A | N/A |
| **Corn_Maize** | 89.0% | 88.9% | N/A | N/A | N/A | N/A |
| **Guava** | 92.0% | 91.7% | N/A | N/A | N/A | N/A |
| **Cucumber_Pumpkin** | 74.4% | 75.2% | N/A | N/A | N/A | N/A |
| **Apple** | 83.0% | 82.6% | N/A | N/A | N/A | N/A |

---

## 17. Domain Shift Analysis

Domain shift deltas $(\Delta\text{Accuracy}, \Delta\text{Macro-F1})$ are uncalculated due to absent field data. Controlled laboratory benchmark scores are **never** presented as field scores.

## 18. Edge-vs-Server Runtime Parity

PyTorch server model and ONNX FP16 / INT8 runtimes exhibit **100% prediction agreement** and $< 0.0002$ logit discrepancy on benchmark evaluations. On real field images: **`FIELD DATA NOT YET AVAILABLE`**.

## 19. Safety Analysis & CIBRC Regulatory Compliance

The defense-in-depth pipeline remains active: `ImageQualityGate` $\to$ `CropModelRegistry` $\to$ `VisionPredictionValidator` $\to$ `AgriculturalRAGService` $\to$ `SafetyEngine`. Banned chemicals (e.g. Monocrotophos) are strictly blocked. Offline mode disables chemical prescriptions. Multi-disease cases are marked `MULTI_LABEL_NOT_SUPPORTED` and abstained.

## 20. Acceptance-Gate Decision

- **Tomato**: Decision = `PENDING`, Status = `FIELD_PENDING`. (FIELD DATA NOT YET AVAILABLE. No on-farm smartphone images collected.)
- **Chilli**: Decision = `PENDING`, Status = `FIELD_PENDING`. (FIELD DATA NOT YET AVAILABLE. No on-farm smartphone images collected.)
- **Rice**: Decision = `REJECTED`, Status = `RESEARCH_ONLY`. (Rice is permanently classified as RESEARCH_ONLY and barred from farmer-facing diagnosis.)
- **Potato**: Decision = `PENDING`, Status = `FIELD_PENDING`. (FIELD DATA NOT YET AVAILABLE. No on-farm smartphone images collected.)
- **Sugarcane**: Decision = `PENDING`, Status = `FIELD_PENDING`. (FIELD DATA NOT YET AVAILABLE. No on-farm smartphone images collected.)
- **Banana**: Decision = `PENDING`, Status = `FIELD_PENDING`. (FIELD DATA NOT YET AVAILABLE. No on-farm smartphone images collected.)
- **Corn_Maize**: Decision = `PENDING`, Status = `FIELD_PENDING`. (FIELD DATA NOT YET AVAILABLE. No on-farm smartphone images collected.)
- **Guava**: Decision = `PENDING`, Status = `FIELD_PENDING`. (FIELD DATA NOT YET AVAILABLE. No on-farm smartphone images collected.)
- **Cucumber_Pumpkin**: Decision = `PENDING`, Status = `FIELD_PENDING`. (FIELD DATA NOT YET AVAILABLE. No on-farm smartphone images collected.)
- **Apple**: Decision = `PENDING`, Status = `FIELD_PENDING`. (FIELD DATA NOT YET AVAILABLE. No on-farm smartphone images collected.)

## 21. Operational & Clinical Limitations

1. **Foliar Scope Only**: Only leaf symptoms are identifiable; root rots and vascular wilts cannot be confirmed from leaf photographs.
2. **Single-Label Restriction**: Models abstain on multi-disease combinations.
3. **Symptom Confusion**: Biotic vs abiotic symptoms (e.g. drought stress vs early blight chlorosis) require soil context.

## 22. Recommended Next Steps

1. Begin intake of real smartphone photographs from KVK extension research centers adhering to `docs/PHASE_5_FIELD_IMAGE_COLLECTION_GUIDE.md`.
2. Ingest pilot batches using `python backend/scripts/ingest_field_validation.py`.
3. Run blind evaluation via `python backend/scripts/evaluate_field_validation.py`.
4. Do NOT promote any model to `PRODUCTION_READY` until independent agronomist sign-off is completed.
