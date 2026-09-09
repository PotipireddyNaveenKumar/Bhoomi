from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class AnnotationState(str, Enum):
    CONFIRMED = "CONFIRMED"
    PROBABLE = "PROBABLE"
    UNCERTAIN = "UNCERTAIN"
    UNKNOWN = "UNKNOWN"


class ImageQualityAssessment(str, Enum):
    PASSED = "PASSED"
    BLUR = "BLUR"
    LOW_RESOLUTION = "LOW_RESOLUTION"
    DARK = "DARK"
    OVEREXPOSED = "OVEREXPOSED"
    OCCLUDED = "OCCLUDED"
    EXTREME_ANGLE = "EXTREME_ANGLE"
    CORRUPTED = "CORRUPTED"
    OTHER = "OTHER"


class ModelFieldStatus(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    FIELD_PENDING = "FIELD_PENDING"
    FIELD_EVALUATION_IN_PROGRESS = "FIELD_EVALUATION_IN_PROGRESS"
    FIELD_VALIDATED = "FIELD_VALIDATED"
    FIELD_LIMITED = "FIELD_LIMITED"
    FIELD_UNSAFE = "FIELD_UNSAFE"
    RESEARCH_ONLY = "RESEARCH_ONLY"


class DuplicateStatus(str, Enum):
    CLEAN = "CLEAN"
    REJECT_EXACT_DUPLICATE = "REJECT_EXACT_DUPLICATE"
    FLAG_NEAR_DUPLICATE = "FLAG_NEAR_DUPLICATE"


class LeakageStatus(str, Enum):
    CLEAN = "CLEAN"
    REJECT_BENCHMARK_LEAKAGE = "REJECT_BENCHMARK_LEAKAGE"


class FieldImageMetadata(BaseModel):
    image_id: str
    crop: str
    image_path: str
    actual_disease: str
    location: str
    state: str
    district: str
    crop_stage: str
    lighting_condition: str
    camera_device: str
    image_distance: str
    leaf_condition: str
    occlusion_level: str
    image_quality: str
    expert_label: str
    annotator_confidence: float = Field(..., ge=0.0, le=1.0)
    annotation_source: str
    annotation_date: str

    # Optional and grouping fields (Privacy-Safe)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    farmer_id_hash: Optional[str] = None
    farm_id_hash: Optional[str] = None
    plant_id_hash: Optional[str] = None
    collection_session_id: Optional[str] = None
    capture_timestamp: Optional[str] = None
    device_model: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    camera_distance: Optional[str] = None
    camera_angle: Optional[str] = None
    irrigation_status: Optional[str] = None
    recent_treatment: Optional[str] = None
    disease_condition_type: str = "single"  # single, multiple, healthy, unknown
    weather_context: Optional[str] = None
    soil_context: Optional[str] = None
    variety_cultivar: Optional[str] = None
    field_condition: Optional[str] = None
    background: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def parse_optional_float(cls, v: Any) -> Optional[float]:
        if v == "" or v is None:
            return None
        return float(v)

    @field_validator("image_width", "image_height", mode="before")
    @classmethod
    def parse_optional_int(cls, v: Any) -> Optional[int]:
        if v == "" or v is None:
            return None
        return int(v)

    @field_validator("crop")
    @classmethod
    def validate_crop(cls, v: str) -> str:
        valid_crops = [
            "tomato", "banana", "guava", "corn_maize", "apple",
            "chilli", "cucumber_pumpkin", "sugarcane", "potato", "rice"
        ]
        cleaned = v.strip().lower()
        if cleaned not in valid_crops:
            raise ValueError(f"Invalid crop '{v}'. Must be one of {valid_crops}")
        return cleaned

    @field_validator("farmer_id_hash", "farm_id_hash", "plant_id_hash")
    @classmethod
    def validate_hash_format(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) < 16:
            raise ValueError("Privacy hashes must be valid one-way cryptographic hashes of at least 16 hex characters")
        return v


class ExpertLabelRecord(BaseModel):
    image_id: str
    crop: str
    expert_label: str
    secondary_diseases: Optional[str] = ""
    disease_condition_type: str = "single"  # single, multiple, healthy, unknown
    is_multi_label: bool = False
    annotation_state: AnnotationState = AnnotationState.CONFIRMED
    pathogen_type: str = "unknown"
    expert_id: str
    review_date: str
    quality_assessment: ImageQualityAssessment = ImageQualityAssessment.PASSED
    notes: Optional[str] = ""


class ManifestItem(BaseModel):
    image_id: str
    crop: str
    image_path: str
    image_hash: str
    perceptual_hash: str
    image_size_bytes: int
    image_width: int
    image_height: int
    metadata_valid: bool
    privacy_valid: bool
    duplicate_status: str
    benchmark_leakage_status: str
    expert_label_status: str
    included_in_evaluation: bool
    rejection_reasons: List[str] = []
    duplicate_classification: str = "UNIQUE"  # EXACT_DUPLICATE, NEAR_DUPLICATE, UNIQUE, UNKNOWN
    provenance_source: Optional[str] = None


class FieldDatasetManifest(BaseModel):
    run_id: str
    timestamp: str
    total_submitted: int
    accepted_for_eval: int
    rejected_count: int
    flagged_near_duplicate_count: int
    items: List[ManifestItem]
    quality_report: Optional[Dict[str, Any]] = None


class FieldFailureCase(BaseModel):
    image_id: str
    crop: str
    expert_label: str
    predicted_disease: str
    confidence: float
    uncertainty_status: str
    failure_category: str
    details: str


class ConfidenceBucketMetrics(BaseModel):
    bucket_range: str
    sample_count: int
    correct_count: int
    accuracy: float


class CropFieldEvaluationSummary(BaseModel):
    crop: str
    total_images: int
    evaluated_images: int
    quality_gate_passed: int
    quality_gate_rejected: int
    rejection_reasons: Dict[str, int]
    accuracy: float
    macro_precision: float
    macro_recall: float
    macro_f1: float
    weighted_f1: float
    abstention_rate: float
    ood_rejection_rate: float
    low_confidence_rate: float
    mean_confidence: float
    median_confidence: float
    confidence_buckets: List[ConfidenceBucketMetrics]
    confusion_matrix: List[List[int]]
    per_class_metrics: Dict[str, Any]
    benchmark_accuracy: float
    benchmark_macro_f1: float
    delta_accuracy: float
    delta_macro_f1: float
    current_status: ModelFieldStatus
    field_validation_statement: str
    high_confidence_error_count: int = 0
    low_confidence_correct_count: int = 0
    probable_accuracy: Optional[float] = None
    probable_macro_f1: Optional[float] = None
    failure_cases: List[FieldFailureCase] = []
    farm_count: int = 0
    plant_count: int = 0
    session_count: int = 0
    device_count: int = 0
    multi_disease_unsupported_count: int = 0
    group_level_metrics: Dict[str, Any] = {}
    edge_vs_server_parity: Dict[str, Any] = {}


# ============================================================================
# PHASE 6 STEP 4: LONGITUDINAL FIELD PILOT & AUDIT SCHEMAS
# ============================================================================

class PilotSystemStatus(str, Enum):
    SOFTWARE_TESTED = "SOFTWARE_TESTED"
    PILOT_DATA_PENDING = "PILOT_DATA_PENDING"
    PILOT_DATA_INGESTED = "PILOT_DATA_INGESTED"
    EXPERT_REVIEW_PENDING = "EXPERT_REVIEW_PENDING"
    FIELD_VALIDATED = "FIELD_VALIDATED"
    PRODUCTION_READY = "PRODUCTION_READY"


class ProvenanceSourceType(str, Enum):
    FARMER_CAPTURED = "FARMER_CAPTURED"
    EXPERT_ANNOTATED = "EXPERT_ANNOTATED"
    FIELD_AGENT = "FIELD_AGENT"
    DEVICE_CAPTURE = "DEVICE_CAPTURE"
    SYSTEM_GENERATED = "SYSTEM_GENERATED"
    IMPORTED_DATASET = "IMPORTED_DATASET"


class DataProvenance(BaseModel):
    source_type: ProvenanceSourceType
    source_reference: str
    collected_at: Optional[str] = None
    imported_at: str
    collector_id_hash: Optional[str] = None
    annotation_source: Optional[str] = None
    verification_status: str = "UNVERIFIED"


class DuplicateClassification(str, Enum):
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    NEAR_DUPLICATE = "NEAR_DUPLICATE"
    UNIQUE = "UNIQUE"
    UNKNOWN = "UNKNOWN"


class VoicePilotRecord(BaseModel):
    audio_id: str
    language: str
    transcript: str
    transcript_source: str = "field_recording"
    stt_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    intent: Optional[str] = None
    intent_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    noise_condition: str = "normal"  # normal, tractor, wind, crowd, rain
    device: str = "smartphone"
    dialect_region: Optional[str] = None
    provenance: Optional[DataProvenance] = None
    consent_obtained: bool = True
    anonymized: bool = True


class TaskOutcomeRecord(BaseModel):
    task_id: str
    task_type: str
    assigned_at: str
    due_at: str
    completed_at: Optional[str] = None
    postponed_at: Optional[str] = None
    skipped_at: Optional[str] = None
    completion_source: Optional[str] = None  # farmer_voice, farmer_app, auto, unknown
    farmer_reported_outcome: Optional[str] = None
    verified_outcome: Optional[str] = None
    farm_id_hash: Optional[str] = None
    crop: Optional[str] = None
    crop_stage: Optional[str] = None
    weather_condition: Optional[str] = None
    language: Optional[str] = None


class RecommendationAuditRecord(BaseModel):
    audit_id: str
    recommendation_trace_id: str
    recommendation_timestamp: str
    crop: str
    system_recommendation: Dict[str, Any]
    farm_state_snapshot: Dict[str, Any]
    task_generated: Optional[Dict[str, Any]] = None
    farmer_action: Optional[str] = None
    farmer_reported_outcome: Optional[str] = None
    expert_verification: Optional[str] = None
    final_outcome: Optional[str] = None
    provenance: DataProvenance


class ExpertReviewClassification(str, Enum):
    VALID = "VALID"
    PARTIALLY_VALID = "PARTIALLY_VALID"
    INVALID = "INVALID"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    SAFETY_CONCERN = "SAFETY_CONCERN"


class AgronomicExpertReviewRecord(BaseModel):
    review_id: str
    recommendation_id: str
    expert_id_hash: str
    review_timestamp: str
    classification: ExpertReviewClassification
    crop: str
    crop_stage: str
    evidence_evaluated: Dict[str, Any]
    weather_context_valid: bool = True
    soil_context_valid: bool = True
    health_observation_valid: bool = True
    safety_result_valid: bool = True
    correction: Optional[str] = None
    explanation: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reference_source: Optional[str] = None
    original_recommendation_preserved: bool = True


class RAGSourceAuditFlag(str, Enum):
    VALID = "VALID"
    MISSING_SOURCE = "MISSING_SOURCE"
    LOW_AUTHORITY_SOURCE = "LOW_AUTHORITY_SOURCE"
    OUTDATED_SOURCE = "OUTDATED_SOURCE"
    REGION_MISMATCH = "REGION_MISMATCH"
    CROP_MISMATCH = "CROP_MISMATCH"


class RAGSourceAuditRecord(BaseModel):
    audit_id: str
    trace_id: str
    crop: str
    state: Optional[str] = None
    source_exists: bool
    source_authority: str  # high (ICAR/FAO), medium (KVK), low (unknown/blog)
    source_citation: str
    crop_relevance: bool
    state_relevance: bool
    publication_date: Optional[str] = None
    section_page: Optional[str] = None
    flag: RAGSourceAuditFlag = RAGSourceAuditFlag.VALID
    original_trace_preserved: bool = True


class PilotQualityReport(BaseModel):
    run_id: str
    timestamp: str
    total_records: int = 0
    accepted: int = 0
    rejected: int = 0
    exact_duplicates: int = 0
    near_duplicates: int = 0
    missing_metadata: int = 0
    invalid_metadata: int = 0
    missing_labels: int = 0
    privacy_violations: int = 0
    unsupported_crop: int = 0
    unsupported_language: int = 0
    corrupt_media: int = 0
    provenance_failures: int = 0
    rejection_details: List[str] = []

