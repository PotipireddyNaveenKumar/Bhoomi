from enum import Enum
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.services.rag.evidence_model import CanonicalSourceCitation, CanonicalEvidenceItem, EvidenceStatus


class XAICapabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE_FOR_CURRENT_MODEL = "UNAVAILABLE_FOR_CURRENT_MODEL"
    HEURISTIC_ATTRIBUTION = "HEURISTIC_ATTRIBUTION"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DEGRADED_QUALITY = "DEGRADED_QUALITY"


class FeatureContribution(BaseModel):
    """
    Individual feature contribution derived from exact model SHAP attributions.
    """
    feature: str
    value: Any
    shap_value: float
    impact_direction: str = "positive"  # positive, negative, neutral
    display_name: Optional[str] = None
    display_text: Optional[str] = None


class ModelExplanation(BaseModel):
    """
    Direct model explanation backed by actual model SHAP values and legitimate confidence.
    """
    model_name: str
    model_version: Optional[str] = None
    prediction: Any
    input_features_used: Dict[str, Any]
    top_positive_factors: List[FeatureContribution] = Field(default_factory=list)
    top_negative_factors: List[FeatureContribution] = Field(default_factory=list)
    all_contributions: List[FeatureContribution] = Field(default_factory=list)
    base_value: Optional[float] = None
    confidence: Optional[float] = None
    explanation_summary: str
    xai_status: str = XAICapabilityStatus.AVAILABLE.value


class VisionHeatmapExplanation(BaseModel):
    """
    Deep learning vision pathology explanation via authentic Grad-CAM activations.
    """
    predicted_disease: str
    model_identifier: str
    model_version: str
    target_class: str
    heatmap: Optional[List[List[float]]] = None
    heatmap_dimensions: Optional[List[int]] = None
    localization_metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None
    xai_status: str = XAICapabilityStatus.AVAILABLE.value
    limitations: List[str] = Field(default_factory=list)


class RAGEvidenceExplanation(BaseModel):
    """
    RAG evidence audit layer linking retrieved agricultural domain knowledge.
    """
    evidence_status: str = EvidenceStatus.SUFFICIENT.value
    retrieved_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    citation_identifiers: List[str] = Field(default_factory=list)
    citations: List[CanonicalSourceCitation] = Field(default_factory=list)
    explanation_summary: str
    is_sufficient: bool = True


class LiveDataExplanation(BaseModel):
    """
    Live environmental and market data provenance audit trail.
    """
    weather: Optional[Dict[str, Any]] = None
    market: Optional[Dict[str, Any]] = None
    summary: str = ""


class ExplanationResult(BaseModel):
    """
    Canonical structured explanation representation combining:
    1. MODEL EXPLANATION (SHAP or Grad-CAM)
    2. RAG EVIDENCE (Citations & Authority Tiers)
    3. LIVE DATA (Weather & Market Provenance)
    4. LIMITATIONS & WHY summary
    """
    decision_id: str
    decision_type: str
    prediction: Any
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    xai_status: str = XAICapabilityStatus.AVAILABLE.value
    model_explanation: Optional[ModelExplanation] = None
    vision_explanation: Optional[VisionHeatmapExplanation] = None
    rag_evidence: Optional[RAGEvidenceExplanation] = None
    live_data: Optional[LiveDataExplanation] = None
    top_factors: List[FeatureContribution] = Field(default_factory=list)
    citations: List[CanonicalSourceCitation] = Field(default_factory=list)
    confidence: Optional[float] = None
    why_summary: str
    evidence_summary: str
    current_data_summary: str
    limitations: List[str] = Field(default_factory=list)
    locale: str = "en"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
