"""
Unit, Integration, and Semantic Test Suite for BHOOMI Production RAG Upgrade.
Validates all Step 42 required tests:
- test_query_understanding
- test_query_rewriting
- test_metadata_filtering
- test_hybrid_retrieval
- test_crop_relevance
- test_topic_relevance
- test_location_relevance
- test_authority_ranking
- test_reranking
- test_relevance_threshold
- test_context_builder
- test_source_attribution
- test_grounding
- test_no_hallucination
- test_no_irrelevant_fallback
- test_cache_isolation
- test_multilingual_retrieval
- test_conversation_context
- test_task_does_not_override_question
"""
import pytest
from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput, RAGEvidenceOutput
from app.services.rag.query_understanding import QueryUnderstandingService, QueryUnderstandingResult
from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.reranker import AgriculturalReranker, RerankedChunk
from app.services.rag.context_builder import ContextBuilder, StructuredContextObject
from app.services.rag.grounding_validator import GroundingValidator
from app.services.voice.intent_service import IntentNormalizationService
from app.schemas.voice_intent import VoiceIntentType


@pytest.fixture(autouse=True)
def setup_rag():
    AgriculturalRAGService._initialize_corpus()


def test_query_understanding():
    # Telugu chilli symptom query
    u1 = QueryUnderstandingService.understand("మిరప ఆకులు ముడుచుకుంటున్నాయి. ఎందుకు?")
    assert u1.language == "te"
    assert u1.crop == "chilli"
    assert "leaf_curling" in u1.symptoms
    assert u1.intent in ["CROP_SYMPTOM", "PEST_QUERY"]

    # Hindi tomato blight query
    u2 = QueryUnderstandingService.understand("टमाटर की पत्तियों पर काले और भूरे धब्बे दिखाई दे रहे हैं")
    assert u2.language == "hi"
    assert u2.crop == "tomato"
    assert "spots_blight" in u2.symptoms

    # Unknown crop/location must NOT be fabricated (Step 3 non-negotiable)
    u3 = QueryUnderstandingService.understand("How much fertilizer should I apply?")
    assert u3.crop is None
    assert u3.location is None
    assert u3.intent == "FERTILIZER_QUERY"


def test_query_rewriting():
    u = QueryUnderstandingService.understand("మిరప ఆకులు ముడుచుకుంటున్నాయి. ఎందుకు?")
    rewrites = QueryRewriter.rewrite(u)
    assert len(rewrites) >= 3
    # Check that rewrites include canonical concepts without unsupported assumptions
    assert any("chilli leaf curling causes" in r for r in rewrites)
    assert any("symptoms" in r or "pests" in r for r in rewrites)
    # Ensure rewrites do not claim certainty like "Chilli has virus disease"
    assert not any("chilli definitely has" in r.lower() for r in rewrites)


def test_metadata_filtering():
    corpus = AgriculturalRAGService._load_knowledge_corpus()
    assert len(corpus) >= 30
    for doc in corpus:
        meta = doc.get("metadata", {})
        assert "crop" in meta
        assert "topic" in meta
        assert "source_authority" in meta
        assert "document_title" in meta


def test_hybrid_retrieval():
    # Dense semantic + Lexical hybrid search
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="chilli leaf curl virus whitefly thrips",
        crop="chilli",
        top_k=3
    ))
    assert res.evidence_found is True
    assert len(res.evidence_passages) >= 1
    assert len(res.citations) >= 1
    assert res.verification_status in ["verified", "RAG_SUCCESS"]


def test_crop_relevance():
    # Step 8: Query about chilli MUST retrieve chilli documents, not tomato or rice
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="Why are chilli leaves curling?",
        crop="chilli",
        top_k=3
    ))
    assert res.evidence_found is True
    for chunk in res.reranked_chunks:
        chunk_crop = chunk.get("metadata", {}).get("crop", "general")
        assert chunk_crop in ["chilli", "general"]


def test_topic_relevance():
    # Step 9: Symptom query must NOT retrieve market price documents
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="మిరప ఆకులు ముడుచుకుంటున్నాయి. ఎందుకు?",
        top_k=5
    ))
    assert res.evidence_found is True
    chunk_ids = [c.get("chunk_id") for c in res.reranked_chunks]
    assert "KB-MKT-HARVEST-001" not in chunk_ids  # Market doc excluded


def test_location_relevance():
    # Step 10: Location influences score but does not discard national ICAR guidance
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="How should I manage chilli thrips in Guntur?",
        crop="chilli",
        district="Guntur",
        state="Andhra Pradesh",
        top_k=3
    ))
    assert res.evidence_found is True
    top_auth = res.citations[0].authority
    assert "ICAR" in top_auth or "ANGRAU" in top_auth


def test_authority_ranking():
    # Step 11: Tier 1 ICAR sources are weighted higher
    scores = AgriculturalReranker.AUTHORITY_TIER_SCORES
    assert scores["tier_1"] > scores["tier_2"]
    assert scores["tier_2"] > scores["tier_3"]
    assert scores["tier_3"] > scores["tier_4"]


def test_reranking():
    # Step 12: Candidates are reranked by composite relevance score
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="How to manage tomato early blight lesions?",
        crop="tomato",
        top_k=3
    ))
    assert res.evidence_found is True
    assert len(res.reranked_chunks) >= 1
    top_chunk = res.reranked_chunks[0]
    assert top_chunk.get("metadata", {}).get("crop") == "tomato"


def test_relevance_threshold():
    # Step 13: Completely gibberish query should be rejected under MIN_RELEVANCE_THRESHOLD
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="quantum mechanics superstring theory spacecraft astronaut",
        top_k=3
    ))
    assert res.evidence_found is False
    assert res.verification_status in ["RAG_LOW_RELEVANCE", "RAG_NO_RESULTS"]
    assert len(res.evidence_passages) == 0


def test_context_builder():
    # Step 17: Structured Context Object isolation
    u = QueryUnderstandingService.understand("When should I irrigate my chilli crop?")
    rag_out = AgriculturalRAGService.search(RAGQueryInput(query="When should I irrigate my chilli crop?", crop="chilli", top_k=2))
    
    ctx = ContextBuilder.build_context(
        query_info=u,
        reranked_chunks=[
            RerankedChunk(
                chunk_id=c["chunk_id"],
                content=c["content"],
                metadata=c["metadata"],
                retrieval_score=0.85,
                rerank_score=0.88,
                query_relevance=0.8,
                crop_relevance=1.0,
                topic_relevance=1.0,
                location_relevance=0.7,
                authority_score=1.0
            )
            for c in rag_out.reranked_chunks[:2]
        ],
        farm_state=type("MockState", (), {"soil_moisture_awc_pct": 38.0, "soil_tension_kpa": -45.0, "active_crops": ["Chilli"]})(),
        pending_tasks=[type("MockTask", (), {"task_id": "t1", "title": "Morning Drip Irrigation", "status": type("S", (), {"value": "DUE"})(), "reason": "Low moisture"})()]
    )
    assert ctx.has_sufficient_evidence is True
    assert len(ctx.retrieved_evidence) >= 1
    assert ctx.farm_context.get("soil_moisture_awc_pct") == 38.0
    assert len(ctx.task_context) == 1
    
    # Verify prompt instructs LLM not to replace the answer with task
    prompt = ContextBuilder.format_llm_prompt(ctx)
    assert "NEVER make a task status the direct answer" in prompt


def test_source_attribution():
    # Step 20: Every RAG-grounded answer retains source authority, title, and section
    res = AgriculturalRAGService.search(RAGQueryInput(
        query="What is the PM-KISAN scheme financial assistance amount?",
        top_k=2
    ))
    assert res.evidence_found is True
    assert len(res.citations) >= 1
    c = res.citations[0]
    assert c.authority != ""
    assert c.document_title != ""


def test_grounding():
    # Step 19: Grounding validator flags banned pesticides
    ctx = ContextBuilder.build_context(
        query_info=QueryUnderstandingService.understand("How to control thrips?"),
        reranked_chunks=[]
    )
    res_bad = GroundingValidator.validate("You should spray monocrotophos at 2 ml/litre immediately.", ctx)
    assert res_bad.is_grounded is False
    assert res_bad.suggested_action == "reject"
    assert any("monocrotophos" in u for u in res_bad.unsupported_claims)

    res_good = GroundingValidator.validate("Install yellow and blue sticky traps and spray neem oil.", ctx)
    assert res_good.is_grounded is True


def test_no_hallucination():
    # Unsupported price assertions without mandi/tool evidence are flagged
    ctx = ContextBuilder.build_context(
        query_info=QueryUnderstandingService.understand("What is the price of chilli?"),
        reranked_chunks=[]
    )
    res = GroundingValidator.validate("Today chilli is guaranteed selling for ₹45,000 per quintal.", ctx)
    assert res.is_grounded is False
    assert any("financial" in u for u in res.unsupported_claims)


def test_no_irrelevant_fallback():
    # Gibberish queries return RAG_LOW_RELEVANCE and do NOT return unrelated canned text
    res = AgriculturalRAGService.search(RAGQueryInput(query="xyz random text 123", top_k=2))
    assert res.evidence_found is False
    assert "No verified agricultural research documentation found" in res.grounded_summary


def test_cache_isolation():
    # Step 23: Cache keys include crop, language, and intent, preventing pollution
    u_te = QueryUnderstandingService.understand("మిరప ఆకులు ముడుచుకుంటున్నాయి. ఎందుకు?")
    k_te = AgriculturalRAGService._generate_cache_key(RAGQueryInput(query="మిరప ఆకులు ముడుచుకుంటున్నాయి. ఎందుకు?"), u_te)

    u_tom = QueryUnderstandingService.understand("What is today's tomato price?")
    k_tom = AgriculturalRAGService._generate_cache_key(RAGQueryInput(query="What is today's tomato price?"), u_tom)

    assert k_te != k_tom
    assert "te" in k_te
    assert "en" in k_tom
    assert "chilli" in k_te
    assert "tomato" in k_tom


def test_multilingual_retrieval():
    # Step 21: English, Telugu, Hindi, Tamil queries on leaf curling map to the same topic
    q_en = AgriculturalRAGService.search(RAGQueryInput(query="Why are chilli leaves curling?", top_k=2))
    q_te = AgriculturalRAGService.search(RAGQueryInput(query="మిరప ఆకులు ముడుచుకుంటున్నాయి. ఎందుకు?", top_k=2))
    q_hi = AgriculturalRAGService.search(RAGQueryInput(query="मिर्च के पत्ते मुड़ रहे हैं, क्यों?", top_k=2))

    assert q_en.evidence_found is True
    assert q_te.evidence_found is True
    assert q_hi.evidence_found is True

    assert q_en.parsed_crop == "chilli"
    assert q_te.parsed_crop == "chilli"
    assert q_hi.parsed_crop == "chilli"


def test_conversation_context():
    # Step 24: Conversation context updates crop explicitly without cross-query pollution
    u1 = QueryUnderstandingService.understand("My chilli crop is in Guntur.", farmer_context={"location": {"district": "Guntur"}})
    assert u1.crop == "chilli"
    assert u1.location.get("district") == "Guntur"

    # Next query asks about tomato price: chilli context must not force chilli retrieval
    u2 = QueryUnderstandingService.understand("What is today's tomato price?", farmer_context={"active_crops": [{"crop_name": "Chilli"}]})
    assert u2.crop == "tomato"
    assert u2.intent == "MARKET_QUERY"


def test_task_does_not_override_question():
    # Step 16: "మిరప ఆకులు ముడుచుకుంటున్నాయి. ఎందుకు?" must NEVER classify as TASK_WHY
    intent = IntentNormalizationService.parse_intent("మిరప ఆకులు ముడుచుకుంటున్నాయి. ఎందుకు?")
    assert intent.intent_type == VoiceIntentType.PEST_QUERY
    assert intent.intent_type != VoiceIntentType.TASK_WHY
