"""
BHOOMI V2 — Master Stabilization Batch 6 Test Suite
EVIDENCE-GROUNDED RAG 2.0 REGRESSION TESTS

Validates all 21 required test cases:
1. Exact relevant evidence retrieval
2. Metadata filtering
3. Crop-aware retrieval
4. Crop-stage-aware retrieval
5. Location/state-aware retrieval
6. Hybrid retrieval candidate merging
7. 2-Stage Reranking
8. Evidence provenance preservation
9. Citation generation (auditable contract)
10. Sufficient evidence -> LLM allowed
11. Insufficient evidence -> LLM factual generation blocked
12. Empty retrieval -> explicit INSUFFICIENT_EVIDENCE
13. No fabricated citation
14. No fabricated source
15. Market unavailable remains unavailable
16. Weather unavailable remains unavailable
17. English response remains English
18. Telugu response remains Telugu
19. Hindi response remains Hindi
20. Existing Batch 4 provider safety guarantees preserved
21. Existing Batch 5 localization & voice consistency preserved
"""
import pytest
from unittest.mock import patch
import httpx
from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput, RAGEvidenceOutput
from app.services.rag.evidence_model import EvidenceStatus, CanonicalEvidenceItem, CanonicalSourceCitation
from app.services.rag.verification_service import EvidenceSufficiencyGate, LLMVerificationService
from app.services.rag.bm25_retriever import BM25Retriever
from app.services.rag.citation_builder import CitationBuilder
from app.services.rag.reranker import AgriculturalReranker
from app.services.safety.safety_engine import SafetyEngine
from app.services.market.real_provider import RealMarketDataProvider
from app.schemas.market import MarketFreshnessStatus
from app.services.weather.real_provider import RealWeatherProvider
from app.schemas.weather import FreshnessStatus


@pytest.fixture(autouse=True)
def init_rag_corpus():
    AgriculturalRAGService._initialize_corpus(force=True)


# 1. Exact relevant evidence retrieval
def test_1_exact_relevant_evidence_retrieval():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="How to manage thrips and leaf curl virus in chilli?",
        crop="chilli",
        top_k=3
    ))
    assert res.evidence_found is True
    assert res.evidence_status == EvidenceStatus.SUFFICIENT
    assert len(res.canonical_evidence) >= 1
    top_doc = res.canonical_evidence[0]
    assert "chilli" in (top_doc.crop or "").lower()
    assert any(k in top_doc.content.lower() for k in ["thrips", "leaf curl", "fipronil", "azadirachtin"])


# 2. Metadata filtering
def test_2_metadata_filtering():
    corpus = AgriculturalRAGService._load_knowledge_corpus()
    assert len(corpus) > 0
    for doc in corpus:
        meta = doc.get("metadata", {})
        assert "crop" in meta
        assert "topic" in meta
        assert "source_authority" in meta


# 3. Crop-aware retrieval
def test_3_crop_aware_retrieval():
    # Searching for chilli must retrieve chilli, not tomato
    res_chilli = AgriculturalRAGService.search(RAGQueryInput(
        query="management of sucking pests",
        crop="chilli",
        top_k=2
    ))
    assert res_chilli.evidence_found is True
    assert res_chilli.canonical_evidence[0].crop == "chilli"

    # Searching for tomato must retrieve tomato
    res_tomato = AgriculturalRAGService.search(RAGQueryInput(
        query="management of early blight",
        crop="tomato",
        top_k=2
    ))
    assert res_tomato.evidence_found is True
    assert res_tomato.canonical_evidence[0].crop == "tomato"


# 4. Crop-stage-aware retrieval
def test_4_crop_stage_aware_retrieval():
    res_veg = AgriculturalRAGService.search(RAGQueryInput(
        query="fertilizer schedule for chilli",
        crop="chilli",
        crop_stage="vegetative",
        top_k=2
    ))
    assert res_veg.evidence_found is True
    assert len(res_veg.canonical_evidence) > 0
    top = res_veg.canonical_evidence[0]
    assert top.crop_stage in ["vegetative", "all"]


# 5. Location/state-aware retrieval
def test_5_location_state_aware_retrieval():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="fertilizer recommendation for chilli in black soil",
        crop="chilli",
        state="Andhra Pradesh",
        district="Guntur",
        top_k=3
    ))
    assert res.evidence_found is True
    # Guntur / Andhra Pradesh candidate should be prioritized or present
    top_meta = res.canonical_evidence[0]
    assert top_meta.state in ["Andhra Pradesh", "all_india"]


# 6. Hybrid retrieval candidate merging
def test_6_hybrid_retrieval_candidate_merging():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="Scirtothrips dorsalis Azadirachtin neem oil",
        crop="chilli",
        top_k=3
    ))
    assert res.evidence_found is True
    # Verify retrieval_metadata records vector and lexical hits
    meta = res.retrieval_metadata
    assert "vector_hits" in meta
    assert "lexical_hits" in meta
    assert meta["candidates_count"] > 0
    # Top evidence should indicate hybrid, vector, or bm25 method
    methods = [e.retrieval_method for e in res.canonical_evidence]
    assert any(m in ["hybrid", "lexical_bm25", "vector"] for m in methods)


# 7. 2-Stage Reranking
def test_7_reranking_ordering():
    candidates = AgriculturalRAGService._bm25_retriever.search("chilli leaf curl thrips", top_k=10)
    assert len(candidates) > 0
    from app.services.rag.query_understanding import QueryUnderstandingResult
    q_info = QueryUnderstandingResult(
        original_query="chilli leaf curl thrips",
        normalized_query="chilli leaf curl thrips",
        language="en",
        intent="PEST_QUERY",
        crop="chilli",
        symptoms=["leaf_curling"]
    )
    reranked = AgriculturalReranker.rerank(candidates, q_info, top_k=3)
    assert len(reranked) > 0
    # Verify scores are sorted strictly descending
    scores = [r.rerank_score for r in reranked]
    assert scores == sorted(scores, reverse=True)


# 8. Evidence provenance preservation
def test_8_evidence_provenance_preservation():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="chilli leaf curl virus management",
        crop="chilli",
        top_k=1
    ))
    assert res.evidence_found is True
    ev = res.canonical_evidence[0]
    assert ev.document_id is not None and len(ev.document_id) > 0
    assert ev.title is not None and len(ev.title) > 0
    assert ev.source is not None and len(ev.source) > 0
    assert ev.authority_level in ["TIER_1_GOVT_ICAR", "TIER_2_AGRI_UNIVERSITY", "TIER_3_COMMODITY_BOARD", "TIER_4_GENERAL"]
    assert ev.relevance_score > 0.5


# 9. Citation generation (auditable contract)
def test_9_citation_generation():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="recommended fertilizer schedule for chilli",
        crop="chilli",
        top_k=2
    ))
    assert len(res.canonical_citations) >= 1
    cit = res.canonical_citations[0]
    assert cit.citation_id == "[1]"
    assert cit.document_title is not None
    assert cit.authority is not None
    assert cit.authority_level in ["TIER_1_GOVT_ICAR", "TIER_2_AGRI_UNIVERSITY", "TIER_3_COMMODITY_BOARD", "TIER_4_GENERAL"]


# 10. Sufficient evidence -> LLM allowed
def test_10_sufficient_evidence_llm_allowed():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="How to manage thrips in chilli?",
        crop="chilli"
    ))
    assert res.evidence_status == EvidenceStatus.SUFFICIENT
    assert res.evidence_found is True


# 11. Insufficient evidence -> LLM factual generation blocked
def test_11_insufficient_evidence_blocked():
    # Crop mismatch between candidate and query triggers INSUFFICIENT
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="How to manage dragon fruit bacterial canker in cold weather?",
        crop="dragon_fruit"
    ))
    assert res.evidence_status in [EvidenceStatus.INSUFFICIENT, EvidenceStatus.UNAVAILABLE]
    assert res.evidence_found is False
    assert len(res.canonical_evidence) == 0
    assert len(res.canonical_citations) == 0
    assert "consult your local" in res.grounded_summary or "tell me which crop" in res.grounded_summary or "No verified" in res.grounded_summary


# 12. Empty retrieval -> explicit INSUFFICIENT / UNAVAILABLE
def test_12_empty_retrieval_explicit_unavailable():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="zxqw987123 completely non-existent term"
    ))
    assert res.evidence_status in [EvidenceStatus.UNAVAILABLE, EvidenceStatus.INSUFFICIENT]
    assert res.evidence_found is False
    assert res.confidence == 0.0 or res.confidence < 0.55


# 13. No fabricated citation
def test_13_no_fabricated_citation():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="qwertyuiop random nonsense without knowledge"
    ))
    assert res.evidence_status in [EvidenceStatus.UNAVAILABLE, EvidenceStatus.INSUFFICIENT]
    assert len(res.citations) == 0
    assert len(res.canonical_citations) == 0


# 14. No fabricated source
def test_14_no_fabricated_source():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="asdfghjkl random string"
    ))
    assert res.authority_tier == "none"
    for cit in res.canonical_citations:
        assert False, "No citation should be constructed on missing evidence"


# 15. Market unavailable remains unavailable
@pytest.mark.asyncio
async def test_15_market_unavailable_remains_unavailable():
    # When market provider has no live price, RAG does not fabricate today's price
    provider = RealMarketDataProvider(api_key=None)
    res = await provider.fetch_prices(commodity="NonExistentCropX", district="UnknownDistrict")
    assert res.freshness == MarketFreshnessStatus.UNAVAILABLE.value
    assert res.best_net_realization is None
    assert res.mandi_options == []


# 16. Weather unavailable remains unavailable
@pytest.mark.asyncio
async def test_16_weather_unavailable_remains_unavailable():
    # Weather safety semantics preserved from Batch 4
    provider = RealWeatherProvider(api_key=None, provider_type="openmeteo")
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Network unreachable")):
        res = await provider.get_current_and_forecast("Guntur")
        assert res.freshness == FreshnessStatus.UNAVAILABLE.value
        assert res.current.temperature_c is None


# 17. English response remains English
def test_17_english_locale_preservation():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="How to manage chilli thrips?",
        language="en"
    ))
    assert res.parsed_language == "en"
    msg = EvidenceSufficiencyGate.get_insufficient_message(language="en")
    assert "No verified agricultural research documentation" in msg or "I do not have enough" in msg


# 18. Telugu response remains Telugu
def test_18_telugu_locale_preservation():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="మిరపలో తామర పురుగుల నివారణ ఎలా?",
        language="te"
    ))
    assert res.parsed_language == "te"
    msg = EvidenceSufficiencyGate.get_insufficient_message(language="te")
    assert "వ్యవసాయ పరిశోధనా సమాచారం" in msg


# 19. Hindi response remains Hindi
def test_19_hindi_locale_preservation():
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="मिर्च में थ्रिप्स कीट की रोकथाम कैसे करें?",
        language="hi"
    ))
    assert res.parsed_language == "hi"
    msg = EvidenceSufficiencyGate.get_insufficient_message(language="hi")
    assert "कृषि अनुसंधान जानकारी" in msg


# 20. Batch 4 provider safety guarantees preserved
def test_20_batch4_safety_preserved():
    # Verify SafetyEngine banned chemicals gate
    eval_result = SafetyEngine.evaluate("You should spray monocrotophos or phorate immediately.")
    assert "banned" in " ".join(eval_result.warnings).lower() or eval_result.is_safe is False


# 21. Batch 5 localization & voice consistency preserved
def test_21_batch5_all_six_locales_supported():
    for loc in ["en", "te", "hi", "ta", "kn", "ml"]:
        msg = EvidenceSufficiencyGate.get_insufficient_message(language=loc)
        assert len(msg) > 10, f"Insufficient message missing for locale {loc}"
