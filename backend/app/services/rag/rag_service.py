import re
import math
import os
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.services.rag.vector_store import (
    VectorStore, InMemoryVectorStore, ChromaVectorStore, DocumentChunk, SearchResult
)
from app.services.rag.bm25_retriever import BM25Retriever
from app.services.rag.citation_builder import CitationBuilder, Citation
from app.services.rag.evidence_model import (
    EvidenceStatus, CanonicalEvidenceItem, CanonicalSourceCitation, RAGSufficiencyResult
)
from app.services.rag.embedding_provider import EmbeddingProviderFactory
from app.services.rag.query_understanding import QueryUnderstandingService, QueryUnderstandingResult
from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.reranker import AgriculturalReranker, RerankedChunk
from app.services.rag.context_builder import ContextBuilder, StructuredContextObject
from app.services.rag.grounding_validator import GroundingValidator, GroundingValidationResult
from app.services.rag.verification_service import EvidenceSufficiencyGate, LLMVerificationService
from app.core.config import settings
from app.core.logging import logger


class RAGQueryInput(BaseModel):
    query: str = Field(...)
    language: Optional[str] = Field(default=None)
    intent: Optional[str] = Field(default=None)
    crop: Optional[str] = Field(default=None)
    crop_stage: Optional[str] = Field(default=None)
    location: Optional[Dict[str, Optional[str]]] = Field(default=None)
    state: Optional[str] = Field(default=None)
    district: Optional[str] = Field(default=None)
    topic: Optional[str] = Field(default=None)
    symptoms: Optional[List[str]] = Field(default=None)
    time_context: Optional[str] = Field(default=None)
    top_k: int = Field(default=5, ge=1, le=20)
    farmer_context: Optional[Dict[str, Any]] = None
    farm_context: Optional[Dict[str, Any]] = None
    farm_id: Optional[str] = None
    min_threshold: Optional[float] = None


class RAGEvidenceOutput(BaseModel):
    query: str
    evidence_found: bool
    evidence_status: EvidenceStatus = Field(default=EvidenceStatus.SUFFICIENT)
    evidence_passages: List[str]
    citations: List[Citation]
    canonical_evidence: List[CanonicalEvidenceItem] = Field(default_factory=list)
    canonical_citations: List[CanonicalSourceCitation] = Field(default_factory=list)
    missing_context_elements: List[str] = Field(default_factory=list)
    confidence: float
    grounded_summary: str
    verification_status: str = "verified"  # verified, RAG_LOW_RELEVANCE, RAG_NO_RESULTS, RAG_UNAVAILABLE, SUFFICIENT, INSUFFICIENT, UNAVAILABLE
    authority_tier: str = "tier_1"
    parsed_language: str = "en"
    parsed_intent: str = "GENERAL_AGRICULTURE"
    parsed_crop: Optional[str] = None
    query_rewrites: List[str] = []
    retrieved_candidates_count: int = 0
    reranked_chunks: List[Dict[str, Any]] = []
    retrieval_metadata: Dict[str, Any] = Field(default_factory=dict)
    debug_trace: Optional[Dict[str, Any]] = None


class AgriculturalRAGService:
    _vector_store: Optional[VectorStore] = None
    _fallback_store: Optional[VectorStore] = None
    _bm25_retriever: Optional[BM25Retriever] = None
    _is_initialized: bool = False
    _query_cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _embed_text(cls, text: str) -> List[float]:
        try:
            return EmbeddingProviderFactory.get_provider().embed_text(text)
        except Exception as e:
            logger.warning(f"EmbeddingProvider failed ({e}), using fallback")
            tokens = re.findall(r'\w+', text.lower())
            return [1.0 / max(1, len(tokens))] * 512

    @classmethod
    def _load_knowledge_corpus(cls) -> List[Dict[str, Any]]:
        candidates = [
            getattr(settings, "RAG_KNOWLEDGE_PATH", "data/rag/verified_knowledge.json"),
            os.path.join(os.getcwd(), "data", "rag", "verified_knowledge.json"),
            os.path.join(os.getcwd(), "backend", "data", "rag", "verified_knowledge.json"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "rag", "verified_knowledge.json"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "rag", "verified_knowledge.json"),
        ]
        file_path = None
        for p in candidates:
            if p and os.path.exists(p):
                file_path = os.path.abspath(p)
                break

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                corpus = []
                for it in items:
                    corpus.append({
                        "id": it.get("id"),
                        "text": it.get("answer"),
                        "metadata": {
                            "id": it.get("id"),
                            "question": it.get("question"),
                            "crop": it.get("crop", "general"),
                            "crop_stage": it.get("crop_stage", "all"),
                            "state": it.get("state", "all_india"),
                            "district": it.get("district", "all"),
                            "soil_type": it.get("soil_type", "all"),
                            "topic": it.get("topic", "agronomy"),
                            "subtopic": it.get("subtopic", ""),
                            "symptoms": it.get("symptoms") or [],
                            "pest": it.get("pest"),
                            "disease": it.get("disease"),
                            "keywords": it.get("keywords") or [],
                            "document": it.get("document_title", it.get("source", "ICAR Extension Advisory")),
                            "document_title": it.get("document_title", it.get("source", "ICAR Extension Advisory")),
                            "authority": it.get("source", "ICAR"),
                            "source": it.get("source", "Ministry of Agriculture & Farmers Welfare"),
                            "source_authority": it.get("source_authority", "tier_1"),
                            "source_type": it.get("source_type", "official_extension"),
                            "publication_date": it.get("publication_date", "2024"),
                            "section": it.get("section", "Agronomic Advisory"),
                            "source_url": it.get("source_url", "https://icar.org.in"),
                            "url_or_ref": it.get("source_url", "https://icar.org.in"),
                            "confidence": it.get("confidence", 0.95),
                            "safety_level": it.get("safety_level", "safe_agronomic")
                        }
                    })
                logger.info(f"Loaded {len(corpus)} verified agricultural documents from {file_path}")
                return corpus
            except Exception as e:
                logger.error(f"Error loading verified knowledge JSON from {file_path}: {e}")

        # In-memory baseline fallback
        return [
            {
                "id": "KB-ICAR-CHILLI-001",
                "text": "For managing chilli leaf curl transmitted by whiteflies and thrips: Install yellow and blue sticky traps (15-20 per acre). Spray 10,000 ppm Azadirachtin (Neem oil) @ 2ml/litre during early vegetative stage. If nymph population crosses threshold (2 thrips/leaf), apply Fipronil 5% SC @ 2ml/litre. Maintain consistent irrigation to prevent water stress.",
                "metadata": {
                    "id": "KB-ICAR-CHILLI-001",
                    "crop": "chilli",
                    "crop_stage": "vegetative",
                    "state": "Andhra Pradesh",
                    "district": "Guntur",
                    "topic": "pest_management",
                    "subtopic": "leaf_curling",
                    "symptoms": ["leaf curling"],
                    "document": "ICAR-IIHR Package of Practices for Chilli",
                    "document_title": "ICAR-IIHR Package of Practices for Chilli",
                    "authority": "Indian Council of Agricultural Research (ICAR)",
                    "source": "ICAR-IIHR Package of Practices for Chilli",
                    "source_authority": "tier_1",
                    "publication_date": "2024-01-15",
                    "section": "IPM Guidelines for Solanaceous Crops",
                    "source_url": "https://iihr.res.in/package-practices-chilli",
                    "url_or_ref": "https://iihr.res.in/package-practices-chilli"
                }
            }
        ]

    @classmethod
    def _initialize_corpus(cls, force: bool = False):
        if cls._is_initialized and not force and cls._vector_store is not None and cls._bm25_retriever is not None:
            return

        corpus = cls._load_knowledge_corpus()
        chunks = []
        for item in corpus:
            emb = cls._embed_text(item["text"])
            chunks.append(DocumentChunk(
                chunk_id=item["id"],
                content=item["text"],
                metadata=item["metadata"],
                embedding=emb
            ))

        # 1. Initialize In-Memory Vector Store
        mem_store = InMemoryVectorStore()
        mem_store.add_documents(chunks)
        cls._fallback_store = mem_store

        # 2. Initialize BM25 Lexical Retriever
        bm25 = BM25Retriever()
        bm25.index_documents(chunks)
        cls._bm25_retriever = bm25

        # 3. Initialize Persistent Chroma Store if configured
        if getattr(settings, "VECTOR_DB_PROVIDER", "chroma") == "chroma":
            try:
                chroma_store = ChromaVectorStore(
                    persist_dir=getattr(settings, "CHROMA_PERSIST_DIR", "./data/chroma"),
                    collection_name="bhoomi_agri_kb"
                )
                chroma_store.add_documents(chunks)
                cls._vector_store = chroma_store
                logger.info(f"Initialized persistent ChromaVectorStore with {len(chunks)} chunks.")
            except Exception as e:
                logger.warning(f"Could not initialize ChromaVectorStore ({e}); falling back to InMemoryVectorStore.")
                cls._vector_store = mem_store
        else:
            cls._vector_store = mem_store

        cls._is_initialized = True

    @classmethod
    def _generate_cache_key(cls, query_in: RAGQueryInput, parsed: QueryUnderstandingResult) -> str:
        loc_str = ""
        if parsed.location:
            loc_str = f"{parsed.location.get('state')}_{parsed.location.get('district')}"
        return f"{parsed.language}:{parsed.intent}:{parsed.crop}:{parsed.growth_stage}:{loc_str}:{query_in.query.strip().lower()}"

    @classmethod
    def search(cls, query_in: RAGQueryInput) -> RAGEvidenceOutput:
        cls._initialize_corpus()

        # Step 1: Query Understanding & Normalization
        farm_ctx = query_in.farm_context or query_in.farmer_context or {}
        parsed = QueryUnderstandingService.understand(
            query=query_in.query,
            farmer_context=farm_ctx
        )

        # Step 2: Farm Digital Twin Context Integration (trusted fields only)
        if query_in.crop:
            parsed.crop = query_in.crop.strip().lower()
        elif not parsed.crop:
            if farm_ctx.get("active_crop"):
                parsed.crop = str(farm_ctx.get("active_crop")).strip().lower()
            elif farm_ctx.get("crop"):
                parsed.crop = str(farm_ctx.get("crop")).strip().lower()
            elif farm_ctx.get("active_crops") and isinstance(farm_ctx.get("active_crops"), list) and len(farm_ctx.get("active_crops")) > 0:
                first_item = farm_ctx.get("active_crops")[0]
                if isinstance(first_item, dict) and first_item.get("crop_name"):
                    parsed.crop = str(first_item.get("crop_name")).strip().lower()
                elif isinstance(first_item, str):
                    parsed.crop = first_item.strip().lower()

        if query_in.crop_stage:
            parsed.growth_stage = query_in.crop_stage.strip().lower()
        elif not parsed.growth_stage and farm_ctx.get("crop_stage"):
            parsed.growth_stage = str(farm_ctx.get("crop_stage")).strip().lower()

        if query_in.language:
            parsed.language = query_in.language.strip().lower()
        if query_in.intent:
            parsed.intent = query_in.intent.strip().upper()

        if query_in.state or query_in.district:
            parsed.location = {
                "state": query_in.state or (parsed.location.get("state") if parsed.location else None),
                "district": query_in.district or (parsed.location.get("district") if parsed.location else None)
            }
        elif query_in.location:
            parsed.location = query_in.location
        elif not parsed.location and (farm_ctx.get("state") or farm_ctx.get("district")):
            parsed.location = {
                "state": farm_ctx.get("state"),
                "district": farm_ctx.get("district")
            }

        # Step 3: Multi-dimensional Cache Check
        cache_key = cls._generate_cache_key(query_in, parsed)
        if cache_key in cls._query_cache:
            cached_item = cls._query_cache[cache_key]
            if time.time() - cached_item.get("timestamp", 0) < 600:
                logger.debug(f"RAG query cache hit for key: {cache_key}")
                return cached_item["output"]

        # Step 4: Controlled Query Rewriting
        search_queries = QueryRewriter.rewrite(parsed)

        # Step 5: Hybrid Retrieval (Vector + BM25) across query expansions
        candidate_map: Dict[str, SearchResult] = {}
        vector_hits = 0
        lexical_hits = 0

        for sq in search_queries:
            sq_emb = cls._embed_text(sq)

            # 5A: Vector Search
            results = cls._vector_store.search(
                query_embedding=sq_emb,
                top_k=15,
                query_text=sq
            )
            if not results and cls._fallback_store:
                results = cls._fallback_store.search(
                    query_embedding=sq_emb,
                    top_k=15,
                    query_text=sq
                )

            for r in results:
                cid = r.chunk.chunk_id
                r.retrieval_method = "vector"
                vector_hits += 1
                if cid not in candidate_map or r.similarity_score > candidate_map[cid].similarity_score:
                    candidate_map[cid] = r

            # 5B: Lexical BM25 Search
            if cls._bm25_retriever:
                bm25_results = cls._bm25_retriever.search(query_text=sq, top_k=15)
                for br in bm25_results:
                    cid = br.chunk.chunk_id
                    lexical_hits += 1
                    if cid in candidate_map:
                        existing = candidate_map[cid]
                        # Hybrid fusion score
                        hybrid_score = round(min(1.0, 0.55 * existing.similarity_score + 0.45 * br.similarity_score), 4)
                        existing.similarity_score = max(existing.similarity_score, hybrid_score)
                        existing.retrieval_method = "hybrid"
                    else:
                        br.retrieval_method = "lexical_bm25"
                        candidate_map[cid] = br

        candidate_list = list(candidate_map.values())

        # Step 6: Handle Empty Candidate Set
        effective_threshold = query_in.min_threshold or EvidenceSufficiencyGate.MIN_CONFIDENCE_THRESHOLD

        if not candidate_list:
            insufficient_msg = EvidenceSufficiencyGate.get_insufficient_message(parsed.language)
            out = RAGEvidenceOutput(
                query=query_in.query,
                evidence_found=False,
                evidence_status=EvidenceStatus.UNAVAILABLE,
                evidence_passages=[],
                citations=[],
                canonical_evidence=[],
                canonical_citations=[],
                missing_context_elements=["evidence"],
                confidence=0.0,
                grounded_summary=insufficient_msg,
                verification_status="RAG_NO_RESULTS",
                authority_tier="none",
                parsed_language=parsed.language,
                parsed_intent=parsed.intent,
                parsed_crop=parsed.crop,
                query_rewrites=search_queries,
                retrieved_candidates_count=0,
                reranked_chunks=[],
                retrieval_metadata={
                    "evidence_status": EvidenceStatus.UNAVAILABLE.value,
                    "vector_hits": vector_hits,
                    "lexical_hits": lexical_hits,
                    "candidates_count": 0,
                    "threshold": effective_threshold
                }
            )
            return out

        # Step 7: 2-Stage Agricultural Reranking
        reranked_chunks: List[RerankedChunk] = AgriculturalReranker.rerank(
            candidates=candidate_list,
            query_info=parsed,
            top_k=query_in.top_k,
            min_threshold=effective_threshold
        )

        # Step 8: Deterministic Evidence Sufficiency Gate
        sufficiency = EvidenceSufficiencyGate.evaluate(
            retrieved_evidence=reranked_chunks,
            target_crop=parsed.crop,
            target_stage=parsed.growth_stage,
            min_threshold=effective_threshold,
            has_candidates=len(candidate_list) > 0
        )

        if not sufficiency.is_sufficient or sufficiency.status != EvidenceStatus.SUFFICIENT:
            insufficient_msg = EvidenceSufficiencyGate.get_insufficient_message(
                parsed.language,
                sufficiency.missing_context_elements
            )
            v_status = "RAG_NO_RESULTS" if sufficiency.status == EvidenceStatus.UNAVAILABLE else "RAG_LOW_RELEVANCE"
            out = RAGEvidenceOutput(
                query=query_in.query,
                evidence_found=False,
                evidence_status=sufficiency.status,
                evidence_passages=[],
                citations=[],
                canonical_evidence=[],
                canonical_citations=[],
                missing_context_elements=sufficiency.missing_context_elements,
                confidence=sufficiency.confidence,
                grounded_summary=insufficient_msg,
                verification_status=v_status,
                authority_tier="none",
                parsed_language=parsed.language,
                parsed_intent=parsed.intent,
                parsed_crop=parsed.crop,
                query_rewrites=search_queries,
                retrieved_candidates_count=len(candidate_list),
                reranked_chunks=[],
                retrieval_metadata={
                    "evidence_status": sufficiency.status.value,
                    "sufficiency_reason": sufficiency.reason,
                    "vector_hits": vector_hits,
                    "lexical_hits": lexical_hits,
                    "candidates_count": len(candidate_list),
                    "threshold": effective_threshold
                }
            )
            return out

        # Step 9: Assemble Verified Evidence and Canonical Citations
        verified_passages = [rc.content for rc in reranked_chunks]
        verified_metas = [rc.metadata for rc in reranked_chunks]
        citations = CitationBuilder.build_citations(verified_metas)
        canonical_citations = CitationBuilder.build_canonical_citations(verified_metas)
        canonical_evidence = [rc.to_canonical_evidence() for rc in reranked_chunks]

        avg_score = sum(rc.rerank_score for rc in reranked_chunks) / len(reranked_chunks)
        confidence = round(min(0.99, max(0.65, avg_score)), 2)
        summary = verified_passages[0] if verified_passages else ""

        out = RAGEvidenceOutput(
            query=query_in.query,
            evidence_found=True,
            evidence_status=EvidenceStatus.SUFFICIENT,
            evidence_passages=verified_passages,
            citations=citations,
            canonical_evidence=canonical_evidence,
            canonical_citations=canonical_citations,
            missing_context_elements=[],
            confidence=confidence,
            grounded_summary=summary,
            verification_status="verified",
            authority_tier=reranked_chunks[0].metadata.get("source_authority", "tier_1"),
            parsed_language=parsed.language,
            parsed_intent=parsed.intent,
            parsed_crop=parsed.crop,
            query_rewrites=search_queries,
            retrieved_candidates_count=len(candidate_list),
            reranked_chunks=[rc.model_dump() for rc in reranked_chunks],
            retrieval_metadata={
                "evidence_status": EvidenceStatus.SUFFICIENT.value,
                "sufficiency_reason": sufficiency.reason,
                "vector_hits": vector_hits,
                "lexical_hits": lexical_hits,
                "candidates_count": len(candidate_list),
                "top_score": reranked_chunks[0].rerank_score,
                "threshold": effective_threshold
            }
        )

        cls._query_cache[cache_key] = {
            "timestamp": time.time(),
            "output": out
        }

        return out

    @classmethod
    def search_debug(cls, query_in: RAGQueryInput) -> Dict[str, Any]:
        cls._initialize_corpus()

        farm_ctx = query_in.farm_context or query_in.farmer_context or {}
        parsed = QueryUnderstandingService.understand(
            query=query_in.query,
            farmer_context=farm_ctx
        )
        if query_in.crop:
            parsed.crop = query_in.crop.strip().lower()
        if query_in.language:
            parsed.language = query_in.language.strip().lower()

        search_queries = QueryRewriter.rewrite(parsed)
        out = cls.search(query_in)

        return {
            "query": query_in.query,
            "parsed_understanding": parsed.model_dump(),
            "query_rewrites": search_queries,
            "evidence_status": out.evidence_status.value,
            "confidence": out.confidence,
            "retrieved_count": out.retrieved_candidates_count,
            "accepted_count": len(out.canonical_evidence),
            "citations": [c.model_dump() for c in out.canonical_citations],
            "metadata": out.retrieval_metadata,
            "grounded_summary": out.grounded_summary
        }
