from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

RAG_SUFFICIENCY_THRESHOLD: float = 0.50
XAI_EVIDENCE_DISPLAY_THRESHOLD: float = 0.50


class AuthorityTier(str, Enum):
    TIER_1_GOVT_ICAR = "TIER_1_GOVT_ICAR"           # ICAR, DPPQS, MoA&FW, IMD, AGMARKNET, CIBRC
    TIER_2_AGRI_UNIVERSITY = "TIER_2_AGRI_UNIVERSITY" # SAUs (ANGRAU, TNAU, PJTSAU, UAS, KVKs)
    TIER_3_COMMODITY_BOARD = "TIER_3_COMMODITY_BOARD" # Spices Board, Tea/Coffee Board, FAO, CGIAR
    TIER_4_GENERAL = "TIER_4_GENERAL"               # Verified extension manuals, state advisories


class EvidenceStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"       # High-confidence evidence meeting relevance & entity thresholds
    INSUFFICIENT = "INSUFFICIENT"   # Candidates exist but score below threshold or have crop/stage mismatch
    UNAVAILABLE = "UNAVAILABLE"     # No matching documents found or retrieval storage empty


class CanonicalEvidenceItem(BaseModel):
    """
    Standardized, auditable evidence representation preserving complete provenance.
    """
    chunk_id: str
    document_id: str
    title: str
    source: str
    source_url: Optional[str] = None
    crop: Optional[str] = None
    crop_stage: Optional[str] = None
    topic: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    language: str = "en"
    source_date: Optional[str] = None
    authority_level: str = AuthorityTier.TIER_1_GOVT_ICAR.value
    section: Optional[str] = None
    content: str
    relevance_score: float
    retrieval_method: str = "hybrid"  # vector, lexical_bm25, hybrid


class CanonicalSourceCitation(BaseModel):
    """
    Auditable source citation contract for evidence-grounded responses.
    """
    citation_id: str
    document_title: str
    authority: str
    authority_level: str
    section: Optional[str] = None
    source_date: Optional[str] = None
    source_url: Optional[str] = None


class RAGSufficiencyResult(BaseModel):
    """
    Deterministic evidence sufficiency decision gate output.
    """
    status: EvidenceStatus
    confidence: float
    is_sufficient: bool
    missing_context_elements: List[str] = Field(default_factory=list)
    reason: str
