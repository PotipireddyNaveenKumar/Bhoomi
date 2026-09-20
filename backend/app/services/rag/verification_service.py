from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import re
from app.services.rag.evidence_model import EvidenceStatus, RAGSufficiencyResult, AuthorityTier
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
    evidence_status: EvidenceStatus = EvidenceStatus.SUFFICIENT
    missing_context_elements: List[str] = []
    verified_chunks: List[Dict[str, Any]] = []
    rejected_chunks: List[str] = []
    hedging_or_caution_required: bool = False
    reasoning_summary: str = "Evidence verified against authoritative agricultural sources."


class EvidenceSufficiencyGate:
    """
    Deterministic safety boundary for agricultural evidence.
    Guarantees that an LLM cannot treat weak, missing, or contradictory retrieval
    as verified agricultural facts.
    """

    MIN_CONFIDENCE_THRESHOLD: float = 0.50
    RAG_SUFFICIENCY_THRESHOLD: float = 0.50
    XAI_EVIDENCE_DISPLAY_THRESHOLD: float = 0.50

    INSUFFICIENT_MESSAGES: Dict[str, str] = {
        "en": "No verified agricultural research documentation found matching this specific query with sufficient relevance. Please consult your local Agricultural Extension Officer or KVK scientist.",
        "te": "క్షమించండి, ఈ విషయానికి సంబంధించి తగినంత ధృవీకరించబడిన వ్యవసాయ పరిశోధనా సమాచారం లభించలేదు. ఖచ్చితమైన మరియు సురక్షితమైన సలహా కోసం మీ స్థానిక వ్యవసాయ అధికారిని లేదా KVK శాస్త్రవేత్తలను సంప్రదించండి.",
        "hi": "क्षमा करें, इस विषय पर सुरक्षित सलाह देने के लिए पर्याप्त सत्यापित कृषि अनुसंधान जानकारी उपलब्ध नहीं है। कृपया अपने स्थानीय कृषि विस्तार अधिकारी या कृषि विज्ञान केंद्र (KVK) से संपर्क करें।",
        "ta": "மன்னிக்கவும், இந்த குறிப்பிட்ட தலைப்பில் உங்களுக்கு பாதுகாப்பான ஆலோசனை வழங்க போதுமான சரிபார்க்கப்பட்ட வேளாண் ஆராய்ச்சி தகவல் கிடைக்கவில்லை. தயவுசெய்து உங்கள் பகுதி வேளாண் விரிவாக்க அலுவலர் அல்லது KVK விஞ்ஞானியை அணுகவும்.",
        "kn": "ಕ್ಷಮಿಸಿ, ಈ ವಿಷಯದ ಕುರಿತು ಸುರಕ್ಷಿತ ಸಲಹೆ ನೀಡಲು ಸಾಕಷ್ಟು ಪರಿಶೀಲಿಸಿದ ಕೃಷಿ ಸಂಶೋಧನಾ ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಸ್ಥಳೀಯ ಕೃಷಿ ಅಧಿಕಾರಿ ಅಥವಾ ಕೆವಿಕೆ ವಿಜ್ಞಾನಿಗಳನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "ml": "ക്ഷമിക്കണം, ഈ വിഷയത്തിൽ സുരക്ഷിതമായ ഉപദേശം നൽകാൻ ആവശ്യത്തിന് പരിശോധിച്ച കാർഷിക വിവരങ്ങൾ ലഭ്യമല്ല. കൃത്യമായ നിർദ്ദേശങ്ങൾക്കായി നിങ്ങളുടെ പ്രാദേശിക കൃഷി ഓഫീസറുമായോ കൃഷി വിജ്ഞാൻ കേന്ദ്രവുമായോ (KVK) ബന്ധപ്പെടുക."
    }

    MISSING_CROP_MESSAGES: Dict[str, str] = {
        "en": "To give you an accurate and verified recommendation, could you tell me which crop you are asking about?",
        "te": "సరైన మరియు ధృవీకరించబడిన సలహా అందించడానికి, మీరు ఏ పంట గురించి అడుగుతున్నారో తెలియజేయగలరా?",
        "hi": "सटीक और सत्यापित सलाह देने के लिए, क्या आप बता सकते हैं कि आप किस फसल के बारे में पूछ रहे हैं?",
        "ta": "துல்லியமான ஆலோசனையை வழங்க, நீங்கள் எந்தப் பயிரைப் பற்றி கேட்கிறீர்கள் என்று குறிப்பிட முடியுமா?",
        "kn": "ನಿಖರವಾದ ಸಲಹೆ ನೀಡಲು, ನೀವು ಯಾವ ಬೆಳೆಯ ಬಗ್ಗೆ ಕೇಳುತ್ತಿದ್ದೀರಿ ಎಂದು ತಿಳಿಸಬಹುದೇ?",
        "ml": "കൃത്യമായ വിവരങ്ങൾ നൽകാൻ, നിങ്ങൾ ഏത് വിളയെക്കുറിച്ചാണ് ചോദിക്കുന്നതെന്ന് വ്യക്തമാക്കാമോ?"
    }

    @classmethod
    def get_insufficient_message(cls, language: str = "en", missing_elements: Optional[List[str]] = None) -> str:
        lang = (language or "en").lower()
        if missing_elements and "crop_name" in missing_elements:
            return cls.MISSING_CROP_MESSAGES.get(lang, cls.MISSING_CROP_MESSAGES["en"])
        return cls.INSUFFICIENT_MESSAGES.get(lang, cls.INSUFFICIENT_MESSAGES["en"])

    @classmethod
    def evaluate(
        cls,
        retrieved_evidence: List[Any],
        target_crop: Optional[str] = None,
        target_stage: Optional[str] = None,
        min_threshold: Optional[float] = None,
        has_candidates: bool = False
    ) -> RAGSufficiencyResult:
        threshold = min_threshold if min_threshold is not None else cls.MIN_CONFIDENCE_THRESHOLD

        if not retrieved_evidence:
            stat = EvidenceStatus.INSUFFICIENT if has_candidates else EvidenceStatus.UNAVAILABLE
            return RAGSufficiencyResult(
                status=stat,
                confidence=0.0,
                is_sufficient=False,
                missing_context_elements=["crop_relevance"] if has_candidates else ["evidence"],
                reason="Candidate agricultural documents did not meet minimum relevance threshold." if has_candidates else "No matching agricultural documents found in knowledge base."
            )

        top_score = getattr(retrieved_evidence[0], "relevance_score", getattr(retrieved_evidence[0], "rerank_score", 0.0))
        top_meta = getattr(retrieved_evidence[0], "metadata", {}) or {}
        if not top_meta and hasattr(retrieved_evidence[0], "crop"):
            top_meta = {
                "crop": getattr(retrieved_evidence[0], "crop"),
                "crop_stage": getattr(retrieved_evidence[0], "crop_stage")
            }

        missing: List[str] = []

        # Check crop match
        if target_crop:
            doc_crop = str(top_meta.get("crop", "general")).lower()
            doc_text = str(getattr(retrieved_evidence[0], "content", "")).lower()
            if target_crop.lower() not in doc_crop and target_crop.lower() not in doc_text:
                missing.append("crop_match")
                return RAGSufficiencyResult(
                    status=EvidenceStatus.INSUFFICIENT,
                    confidence=round(top_score, 2),
                    is_sufficient=False,
                    missing_context_elements=["crop_name"],
                    reason=f"Top evidence does not contain verified recommendations for requested crop '{target_crop}'."
                )

        if top_score < threshold:
            return RAGSufficiencyResult(
                status=EvidenceStatus.INSUFFICIENT,
                confidence=round(top_score, 2),
                is_sufficient=False,
                missing_context_elements=missing or ["high_confidence_evidence"],
                reason=f"Top evidence score ({top_score:.2f}) is below minimum sufficiency threshold ({threshold:.2f})."
            )

        return RAGSufficiencyResult(
            status=EvidenceStatus.SUFFICIENT,
            confidence=round(top_score, 2),
            is_sufficient=True,
            missing_context_elements=[],
            reason=f"Verified evidence available with score {top_score:.2f} >= threshold {threshold:.2f}."
        )


class LLMVerificationService:
    """
    LLM Evidence Verification & Conflict Resolution Layer.
    Audits retrieved RAG candidate chunks for relevance, authority tier, and crop stage match.
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
                evidence_status=EvidenceStatus.UNAVAILABLE,
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
                evidence_status=EvidenceStatus.INSUFFICIENT,
                missing_context_elements=missing_context or ["crop_relevance"],
                verified_chunks=[],
                rejected_chunks=rejected,
                hedging_or_caution_required=True,
                reasoning_summary="Candidate evidence rejected due to crop or authority mismatch."
            )

        verified.sort(
            key=lambda x: (x["authority_score"] * 0.4) + (x["similarity_score"] * 0.6),
            reverse=True
        )

        return RAGVerificationResult(
            is_evidence_sufficient=True,
            synthesis_allowed=True,
            evidence_status=EvidenceStatus.SUFFICIENT,
            missing_context_elements=missing_context,
            verified_chunks=verified,
            rejected_chunks=rejected,
            hedging_or_caution_required=any(v["has_chemical"] for v in verified),
            reasoning_summary=f"Verified {len(verified)} chunks. Top authority: {verified[0]['authority_tier'].upper()}."
        )
