# BHOOMI V2 — PHASE 6 STEP 4: LONGITUDINAL FIELD PILOT INGESTION & AGRONOMIC AUDIT PIPELINE

## 1. Architecture Overview

BHOOMI V2 Phase 6 Step 4 introduces the production-grade infrastructure required to safely ingest, validate, anonymize, evaluate, and audit real physical field-pilot observations.

```
                                  PHYSICAL FIELD OBSERVATIONS
                       (Real Farmer Photos, Voice Audio, Task Logs)
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │    MIME, Size & Decode Gate     │
                             └──────────────────────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │ Zero-PII Regex & Hash Privacy    │
                             └──────────────────────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │ Exact (MD5) & Perceptual (aHash) │
                             │        Duplicate Engine          │
                             └──────────────────────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │ Data Provenance & Manifest Store │
                             └──────────────────────────────────┘
                                              │
                ┌─────────────────────────────┼─────────────────────────────┐
                ▼                             ▼                             ▼
   ┌──────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────┐
   │    Group-Aware Split     │  │   Voice Field Pilot      │  │  Longitudinal Task &     │
   │  (Zero Leakage Guard)    │  │   Safety Audit Engine    │  │  Recommendation Audit   │
   └──────────────────────────┘  └──────────────────────────┘  └──────────────────────────┘
                │                             │                             │
                ▼                             ▼                             ▼
   ┌──────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────┐
   │ Blind Expert Annotation  │  │ Critical State Mutation  │  │ 4-Tier Agronomic Chain   │
   │ Isolation (Pre-frozen)   │  │ (False Complete/Postpone)│  │ & SafetyEngine Auditing  │
   └──────────────────────────┘  └──────────────────────────┘  └──────────────────────────┘
                │                             │                             │
                └─────────────────────────────┼─────────────────────────────┘
                                              ▼
                             ┌──────────────────────────────────┐
                             │  Statistical Drift Detector      │
                             │       (N >= 30 Threshold)        │
                             └──────────────────────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────┐
                             │ Multi-Dimensional Acceptance Gate│
                             │   (BHOOMI: NOT_PRODUCTION_READY) │
                             └──────────────────────────────────┘
```

---

## 2. Canonical Field Pilot Data Contracts

The pipeline establishes canonical data models in [`app/services/vision/field_validation/schemas.py`](file:///c:/Users/SURESH/SIH/backend/app/services/vision/field_validation/schemas.py):

1. **Image Observation**: `image_id`, `crop`, `image_path`, `capture_timestamp`, `image_hash` (MD5), `perceptual_hash` (64-bit Average Hash).
2. **Farm Anonymization**: Cryptographic one-way SHA-256 hashes (`farmer_id_hash`, `farm_id_hash`, `plant_id_hash`, `collection_session_id`). Raw farmer identities are strictly barred.
3. **Agronomic Metadata**: `state`, `district`, `crop_stage`, `variety_cultivar`, `field_condition`, `leaf_condition`.
4. **Capture Conditions**: `camera_device`, `lighting_condition`, `image_distance`, `camera_angle`, `occlusion_level`, `weather_context`, `soil_context`.
5. **Expert Annotation**: `expert_label`, `expert_confidence`, `expert_id_hash`, `annotation_source`, `annotation_date`, `annotation_state` (`CONFIRMED`, `PROBABLE`, `UNCERTAIN`, `UNKNOWN`).
6. **Voice Pilot Data**: `audio_id`, `language`, `transcript`, `transcript_source`, `stt_confidence`, `intent`, `intent_confidence`, `noise_condition`, `device`, `dialect_region`.
7. **Task Outcome Record**: `task_id`, `task_type`, `assigned_at`, `due_at`, `completed_at`, `postponed_at`, `skipped_at`, `completion_source`, `farmer_reported_outcome`, `verified_outcome`.

---

## 3. Data Provenance

Every pilot record carries an immutable [`DataProvenance`](file:///c:/Users/SURESH/SIH/backend/app/services/vision/field_validation/schemas.py) record:
- **`source_type`**: `FARMER_CAPTURED`, `EXPERT_ANNOTATED`, `FIELD_AGENT`, `DEVICE_CAPTURE`, `SYSTEM_GENERATED`, `IMPORTED_DATASET`.
- **`source_reference`**: File path, trace ID, or hardware capture token.
- **`collected_at`**: Physical capture ISO timestamp.
- **`imported_at`**: System ingestion ISO timestamp.
- **`collector_id_hash`**: Pseudonymous collector hash.
- **`verification_status`**: e.g., `UNVERIFIED`, `PENDING_EXPERT_REVIEW`, `VERIFIED`.

Model predictions are never represented as ground truth.

---

## 4. Ingestion Pipeline

[`FieldPilotIngestionService`](file:///c:/Users/SURESH/SIH/backend/app/services/vision/field_validation/ingest.py) enforces the 12-step validation flow:
```
RAW INPUT
  ↓
FILE VALIDATION (Existence, readability, byte length > 0)
  ↓
MIME VALIDATION (Allowed: JPEG, PNG, WEBP, MPO)
  ↓
SIZE VALIDATION (Max 20MB, min dimension 64x64)
  ↓
HASHING (MD5 file hash + 64-bit Average Hash)
  ↓
DUPLICATE DETECTION (MD5 exact duplicate vs aHash Hamming <= 5)
  ↓
PII CHECK (Zero-tolerance phone numbers, Aadhaar, survey numbers)
  ↓
METADATA VALIDATION (Allowed crop names, stage values)
  ↓
SCHEMA VALIDATION (Pydantic field validation)
  ↓
PROVENANCE RECORD (Immutable source metadata attached)
  ↓
MANIFEST ENTRY (Deterministic JSON manifest logged)
  ↓
QUARANTINE / ACCEPT (Invalid items quarantined; clean items accepted)
```

---

## 5. Duplicate and Near-Duplicate Protection

- **Exact Duplicates (`EXACT_DUPLICATE`)**: Detected via MD5 collision against accepted pilot images. Rejected and quarantined from evaluation datasets.
- **Near Duplicates (`NEAR_DUPLICATE`)**: Flagged using bit-level Hamming distance $\le 5$ on 16-hex-character perceptual average hashes. They are tracked transparently in manifest metrics and isolated from splitting.
- **Unique Records (`UNIQUE`)**: Clean, distinct field observations.
- **Unknown (`UNKNOWN`)**: Unreadable or unhashed observations.

---

## 6. Dataset Split Leakage Prevention

[`FarmSessionGroupManager`](file:///c:/Users/SURESH/SIH/backend/app/services/vision/field_validation/group_evaluator.py) enforces group-aware compound split isolation:
- Grouping keys: `(farm_id_hash, plant_id_hash, collection_session_id)`.
- Images from the same physical plant, collection session, or farm cannot cross between `train`, `validation`, and `test` splits.
- `detect_three_way_leakage` mathematically inspects pair-wise intersections (`train_vs_val`, `train_vs_test`, `val_vs_test`).

---

## 7. Blind Expert Evaluation

To eliminate evaluation bias:
1. `prepare_blind_annotation_packet`: Strips all system predictions, model names, confidence scores, and uncertainty statuses. Experts receive only the raw image, crop identifier, and environmental capture context.
2. Expert labels are captured independently and stored with cryptographic annotator hashes.
3. Only after the blind annotation is sealed are model predictions joined post-hoc (`join_blind_evaluations`) for metrics computation.

---

## 8. Vision Field Metrics

The vision evaluation framework measures:
- Accuracy, Macro-F1, Weighted F1, Per-Class Precision, Recall, Confusion Matrix.
- Calibration and Confidence Distribution.
- High-Confidence Error Rate (critical safety failure if $> 15\%$).
- Abstention Rate, OOD Rejection Rate.
- **Insufficient-Data Transparency**: If $N < 30$, outputs `INSUFFICIENT_DATA` / `GROUP-LEVEL METRICS NOT YET RELIABLE` rather than fabricating statistical performance.

---

## 9. Field Domain Shift Analysis

[`PilotDriftDetector`](file:///c:/Users/SURESH/SIH/backend/app/services/monitoring/pilot_drift.py) analyzes domain shift:
$$\Delta \text{Accuracy} = \text{Accuracy}_{\text{field}} - \text{Accuracy}_{\text{benchmark}}$$
$$\Delta \text{Macro-F1} = \text{Macro-F1}_{\text{field}} - \text{Macro-F1}_{\text{benchmark}}$$
$$\Delta \text{Confidence} = \text{Confidence}_{\text{field}} - \text{Confidence}_{\text{benchmark}}$$
Requires $N \ge 30$ field observations to prevent false alarms.

---

## 10. Voice Field Pilot Audit

[`VoiceFieldPilotAuditService`](file:///c:/Users/SURESH/SIH/backend/app/services/voice/field_audit.py) monitors longitudinal voice interactions:
- STT Accuracy, Intent Accuracy, Action Success Rate.
- **Critical False State Mutations**:
  - `FALSE_COMPLETION`: Completed a task without farmer intent.
  - `FALSE_POSTPONEMENT`: Postponed a task without farmer intent.
  - `FALSE_SKIP`: Skipped a task without farmer intent.
  - `FALSE_TASK_SELECTION`: Executed action on the wrong task.
  - `FALSE_CONFIRMATION`: Executed consequential actions without obtaining explicit confirmation.
- Segmented by language (`te`, `hi`, `ta`, `kn`, `ml`, `en`), noise condition (tractor, wind, crowd), and device.

---

## 11. Voice Safety Audit

Audits voice interactions against:
- `unsafe_action_block_rate`: Verification that chemical/pesticide bypasses are blocked.
- `confirmation_bypass_rate`: Zero-tolerance for skipping required confirmations.
- Ambiguous command rejection without premature state mutation.

---

## 12. Task Longitudinal Adherence Audit

[`TaskLongitudinalAuditService`](file:///c:/Users/SURESH/SIH/backend/app/services/farm_manager/longitudinal_audit.py) measures:
- Completion Rate, Postponement Rate, Skip Rate, Overdue Rate.
- Median Completion Delay (days).
- Segmented by crop and task type.
- Adheres to the $N \ge 30$ minimum sample threshold.

---

## 13. Recommendation Outcome Audit

[`RecommendationOutcomeAuditService`](file:///c:/Users/SURESH/SIH/backend/app/services/farm_manager/longitudinal_audit.py) enforces the 4-tier chain:
$$\text{SYSTEM\_RECOMMENDATION} \rightarrow \text{FARMER\_ACTION} \rightarrow \text{FARMER\_REPORTED\_OUTCOME} \rightarrow \text{VERIFIED\_OUTCOME}$$
Predictions and actual outcomes are never collapsed into a single label.

---

## 14. Agronomic Expert Review Workflow

[`AgronomicExpertReviewService`](file:///c:/Users/SURESH/SIH/backend/app/services/farm_manager/longitudinal_audit.py):
- Experts classify: `VALID`, `PARTIALLY_VALID`, `INVALID`, `INSUFFICIENT_EVIDENCE`, `SAFETY_CONCERN`.
- Experts provide corrections, explanations, and citations.
- Guarantees `original_recommendation_preserved: True` (immutable history).

---

## 15. RAG / Source Audit

[`RAGSourceAuditService`](file:///c:/Users/SURESH/SIH/backend/app/services/farm_manager/longitudinal_audit.py):
- Validates institutional authority (ICAR, FAO, ANGRAU, TNAU, KVK).
- Flags: `MISSING_SOURCE`, `LOW_AUTHORITY_SOURCE`, `REGION_MISMATCH`, `CROP_MISMATCH`.
- Original retrieval trace is preserved.

---

## 16. Agronomic Safety Audit

[`AgronomicSafetyAuditor`](file:///c:/Users/SURESH/SIH/backend/app/services/farm_manager/longitudinal_audit.py):
- Checks prohibited pesticides and restricted active ingredients.
- Enforces flowering-stage pollinator protections and weather restrictions.
- Separately surfaces safety violations regardless of overall model accuracy.

---

## 17. Model Drift Detection

[`PilotDriftDetector`](file:///c:/Users/SURESH/SIH/backend/app/services/monitoring/pilot_drift.py):
- Explicit threshold: $N \ge 30$ samples required.
- Detects Vision Domain Shift, Voice Intent Degradation, and Task Postponement Surges.

---

## 18. Voice Transcript Privacy

- Sanitizes API keys, auth tokens, phone numbers, and 12-digit Aadhaar patterns before surfacing in audit logs.
- Stores only pseudonymous hashes.

---

## 19. REST API Contract

Implemented in [`app/api/v1/pilot.py`](file:///c:/Users/SURESH/SIH/backend/app/api/v1/pilot.py):
- `POST /api/v1/pilot/import`: Ingests image, voice, or task observation.
- `GET /api/v1/pilot/status`: Global telemetry & pilot data availability.
- `GET /api/v1/pilot/metrics`: Vision metrics or `INSUFFICIENT_DATA`.
- `GET /api/v1/pilot/crops/{crop}`: Independent crop-specific status.
- `GET /api/v1/pilot/voice-metrics`: Longitudinal voice audit & safety metrics.
- `GET /api/v1/pilot/task-metrics`: Task completion and delay metrics.
- `GET /api/v1/pilot/drift`: Vision, voice, and task drift detection.
- `GET /api/v1/pilot/acceptance`: Multi-dimensional production readiness checklist.

---

## 20. Acceptance Gate & Crop-Specific Status

[`FieldValidationAcceptanceGate`](file:///c:/Users/SURESH/SIH/backend/app/services/vision/field_validation/acceptance_gate.py):
- **Multi-Dimensional Gate**:
  - `field_data_present` (Must be real physical data)
  - `expert_review_complete` ($\ge 30$ pathologist reviews)
  - `no_leakage` (Zero group leakage)
  - `safety_acceptable` (No safety violations)
  - `vision_acceptable` (Macro-F1 $\ge 0.75$, high-conf errors $\le 5\%$)
  - `voice_acceptable` (0 critical state-changing defects)
  - `task_behavior_acceptable` (Completion rate $\ge 60\%$)
- **Crop Independence**:
  - **Rice**: Strictly `RESEARCH_ONLY`. Barred from farmer-facing promotion.
  - **Tomato, Banana, Guava, Corn**: `PILOT_DATA_PENDING`.
  - **Other crops**: `CANDIDATE` / `NOT_EVALUATED`.

---

## 21. Critical Date/Timezone Hardening (Section 31)

[`TaskIntelligenceEngine.postpone_task`](file:///c:/Users/SURESH/SIH/backend/app/services/farm_manager/task_engine.py):
- Parses existing `due_at` with time-of-day and timezone offset (e.g. `2026-09-04T08:00:00+05:30`).
- Adds `timedelta(days=days_to_postpone)` directly to the datetime object.
- **Preserved**: Friday 08:00:00+05:30 + 2 days = Sunday 08:00:00+05:30.
- Handles pure dates (`YYYY-MM-DD`) and full ISO strings without timestamp destruction.

---

## 22. Production Readiness Status

```
REAL_FIELD_PILOT_DATA: NOT_PRESENT
BHOOMI_V2_STATUS:      NOT_PRODUCTION_READY
RICE_STATUS:           RESEARCH_ONLY
```

BHOOMI V2 remains strictly **`NOT_PRODUCTION_READY`** until physical on-farm pilot observations and independent agronomic certifications are completed.
