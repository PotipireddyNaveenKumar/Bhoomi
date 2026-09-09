import pytest
from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput, RAGEvidenceOutput
from app.services.rag.verification_service import LLMVerificationService
from app.services.rag.embedding_provider import EmbeddingProviderFactory
from app.services.safety.safety_engine import SafetyEngine, SafetyCheckResult
from app.services.memory.farm_memory_v2 import FarmMemoryV2
from app.schemas.chat import ChatMessageResponse, VisualCard
from datetime import datetime, timezone


def test_embedding_provider_generation():
    provider = EmbeddingProviderFactory.get_provider()
    vec = provider.embed_text("How to manage thrips in chilli?")
    assert isinstance(vec, list)
    assert len(vec) > 100
    assert any(v > 0 for v in vec)


def test_rag_verified_knowledge_retrieval():
    AgriculturalRAGService._vector_store = None
    query = RAGQueryInput(query="What is the recommended fertilizer schedule for chilli?", crop="chilli")
    res = AgriculturalRAGService.search(query)
    assert isinstance(res, RAGEvidenceOutput)
    assert res.evidence_found is True
    assert len(res.evidence_passages) > 0
    assert len(res.citations) > 0
    assert res.verification_status == "verified"
    assert res.confidence >= 0.5


def test_rag_crop_mismatch_filtering():
    AgriculturalRAGService._vector_store = None
    candidate_chunks = [
        {
            "chunk_id": "chilli_chunk_1",
            "content": "Apply fipronil for chilli leaf curl thrips.",
            "metadata": {"crop": "chilli", "source_authority": "tier_1", "id": "c1"},
            "similarity_score": 0.9
        }
    ]
    # Search for banana with chilli chunk
    res = LLMVerificationService.verify_retrieval(
        query="How to manage panama wilt?",
        retrieved_chunks=candidate_chunks,
        crop="banana"
    )
    # The chilli chunk should be rejected due to crop mismatch
    assert "chilli_chunk_1" in res.rejected_chunks
    assert res.is_evidence_sufficient is False


def test_rag_authority_tier_ranking():
    chunks = [
        {
            "chunk_id": "tier4_chunk",
            "content": "Random blog recommendation.",
            "metadata": {"crop": "chilli", "source_authority": "tier_4", "id": "t4"},
            "similarity_score": 0.95
        },
        {
            "chunk_id": "tier1_chunk",
            "content": "Official ICAR package of practices recommendation.",
            "metadata": {"crop": "chilli", "source_authority": "tier_1", "id": "t1"},
            "similarity_score": 0.85
        }
    ]
    res = LLMVerificationService.verify_retrieval(
        query="Chilli pest management",
        retrieved_chunks=chunks,
        crop="chilli"
    )
    assert res.is_evidence_sufficient is True
    # Tier 1 chunk should be ranked first due to authority weighting
    assert res.verified_chunks[0]["chunk_id"] == "tier1_chunk"


def test_safety_engine_banned_substance():
    res = SafetyEngine.evaluate("Farmer wants to spray Monocrotophos 36% SL on vegetables", crop="tomato")
    assert res.status == "BLOCK"
    assert res.is_safe is False
    assert any("Monocrotophos" in r for r in res.blocked_reasons)


def test_safety_engine_rice_research_only():
    res = SafetyEngine.evaluate("Spray tricyclazole fungicide for rice blast", crop="rice")
    assert res.status == "BLOCK"
    assert "RESEARCH_ONLY" in res.blocked_reasons[0]


def test_safety_engine_dosage_overdose_modification():
    # Recommended limit is 50.0 ml/acre
    res = SafetyEngine.evaluate("Apply Imidacloprid @ 80 ml per acre for thrips", crop="chilli")
    assert res.status == "MODIFY"
    assert res.is_safe is True
    assert "50.0 ml/acre" in res.modified_text
    assert any("exceeds standard label recommendation" in w for w in res.warnings)


def test_safety_engine_extreme_overdose_blocking():
    # 500 ml/acre is 10x the 50 ml/acre limit
    res = SafetyEngine.evaluate("Spray Imidacloprid @ 500 ml per acre for thrips", crop="chilli")
    assert res.status == "BLOCK"
    assert res.is_safe is False
    assert any("Critical Chemical Hazard" in r for r in res.blocked_reasons)


def test_farm_memory_runtime_and_category():
    entry = FarmMemoryV2.add_memory(
        farmer_id="farmer_test_unit",
        category="PREFERENCE",
        key="preferred_cultivar",
        value="Teja Chilli",
        confidence=0.95
    )
    assert entry.key == "preferred_cultivar"
    mems = FarmMemoryV2.get_memories_by_category("farmer_test_unit", "PREFERENCE")
    assert len(mems) >= 1
    assert mems[-1].value == "Teja Chilli"


def test_chat_response_schema_enrichment():
    resp = ChatMessageResponse(
        id="msg_1",
        session_id="sess_1",
        sender="assistant",
        input_mode="text",
        content="Advisory response",
        intent="CROP_PROTECTION",
        trace_id="tr_12345",
        sources=[{"title": "ICAR Advisory", "authority": "ICAR"}],
        actions=[],
        created_at=datetime.now(timezone.utc)
    )
    assert resp.intent == "CROP_PROTECTION"
    assert resp.trace_id == "tr_12345"
    assert len(resp.sources) == 1
