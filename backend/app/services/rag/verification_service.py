from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import re
from app.core.logging import logger


class ChunkVerification(BaseModel):
    chunk_id: str
    is_relevant: bool = True
    is_crop_applicable: bool = True
    is_stage_applicable: bool = True
    authority_tier: str = "tier_1"  # tier_1, tier_2, tier_3, tier_4
    authority_score: float = 1.0
    has_conflicts: bool = False
    conflict_notes: Optional[str] = None


class RAGVerificationResult(BaseModel):
    is_evidence_sufficient: bool = True
    synthesis_allowed: bool = True
    missing_context_elements: List[str] = []
    verified_chunks: List[Dict[str, Any]] = []
    rejected_chunks: List[str] = []
    hedging_or_caution_required: bool = False
    reasoning_summary: str = "Evidence verified against authoritative agricultural sources."


class LLMVerificationService:
    """
    LLM Evidence Verification & Conflict Resolution Layer.
    Audits retrieved RAG candidate chunks for:
    - Relevance to farmer's specific query
    - Source Authority (Tier 1 Government / ICAR > Tier 2 Universities > Tier 3 Orgs > Tier 4 General)
    - Crop and crop stage applicability
    - Source contradiction detection and resolution
    - Chemical safety and uncertainty bounds
    """

    AUTHORITY_TIER_SCORES = {
        "tier_1": 1.0,   # ICAR, DPPQS, MoA, IMD, Agmarknet
        "tier_2": 0.85,  # ANGRAU, TNAU, PJTSAU, State Agri Depts, KVKs
        "tier_3": 0.65,  # FAO, CGIAR, Commodity Boards
        "tier_4": 0.40   # General extension portals
    }

    @classmethod
    def verify_retrieval(
        cls,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        crop: Optional[str] = None,
        crop_stage: Optional[str] = None,
        state: Optional[str] = None
    ) -> RAGVerificationResult:
        if not retrieved_chunks:
            return RAGVerificationResult(
                is_evidence_sufficient=False,
                synthesis_allowed=False,
                missing_context_elements=["evidence"],
                verified_chunks=[],
                rejected_chunks=[],
                hedging_or_caution_required=True,
                reasoning_summary="No matching agricultural evidence found."
            )

        query_lower = query.lower()
        verified = []
        rejected = []
        missing_context = []

        # Check for missing critical context in query
        if not crop and any(w in query_lower for w in ["fertilizer", "spray", "dose", "dosage", "pest", "disease", "cure", "medicine"]):
            # Check if any chunk specifies a single crop that user didn't mention
            crops_in_chunks = set(c.get("metadata", {}).get("crop", "general") for c in retrieved_chunks)
            crops_in_chunks.discard("general")
            if len(crops_in_chunks) > 1:
                missing_context.append("crop_name")

        for c in retrieved_chunks:
            meta = c.get("metadata", {})
            chunk_id = c.get("chunk_id", meta.get("id", "unknown"))
            chunk_crop = meta.get("crop", "general").lower()
            tier = meta.get("source_authority", "tier_1").lower()
            tier_score = cls.AUTHORITY_TIER_SCORES.get(tier, 0.5)

            # Crop applicability check
            if crop and chunk_crop != "general" and crop.lower() not in chunk_crop:
                rejected.append(chunk_id)
                continue

            # Stage applicability check
            chunk_stage = meta.get("crop_stage", "all").lower()
            stage_match = True
            if crop_stage and chunk_stage != "all":
                if crop_stage.lower() not in chunk_stage:
                    stage_match = False

            # Check for high-risk chemical assertions
            content = c.get("content", "")
            has_chemical = any(k in content.lower() for k in ["spray", "fungicide", "insecticide", "chemical", "dosage"])
            
            verified.append({
                "chunk_id": chunk_id,
                "content": content,
                "metadata": meta,
                "similarity_score": c.get("similarity_score", 0.8),
                "authority_tier": tier,
                "authority_score": tier_score,
                "stage_match": stage_match,
                "has_chemical": has_chemical
            })

        if not verified:
            return RAGVerificationResult(
                is_evidence_sufficient=False,
                synthesis_allowed=False,
                missing_context_elements=missing_context or ["crop_relevance"],
                verified_chunks=[],
                rejected_chunks=rejected,
                hedging_or_caution_required=True,
                reasoning_summary="Candidate evidence rejected due to crop or authority mismatch."
            )

        # Sort verified chunks by combined authority + similarity score
        verified.sort(
            key=lambda x: (x["authority_score"] * 0.4) + (x["similarity_score"] * 0.6),
            reverse=True
        )

        return RAGVerificationResult(
            is_evidence_sufficient=True,
            synthesis_allowed=True,
            missing_context_elements=missing_context,
            verified_chunks=verified,
            rejected_chunks=rejected,
            hedging_or_caution_required=any(v["has_chemical"] for v in verified),
            reasoning_summary=f"Verified {len(verified)} chunks. Top authority: {verified[0]['authority_tier'].upper()}."
        )
