import re
import math
import os
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.services.rag.vector_store import VectorStore, InMemoryVectorStore, ChromaVectorStore, DocumentChunk, SearchResult
from app.services.rag.citation_builder import CitationBuilder, Citation
from app.services.rag.embedding_provider import EmbeddingProviderFactory
from app.services.rag.query_understanding import QueryUnderstandingService, QueryUnderstandingResult
from app.services.rag.query_rewriter import QueryRewriter
from app.services.rag.reranker import AgriculturalReranker, RerankedChunk
from app.services.rag.context_builder import ContextBuilder, StructuredContextObject
from app.services.rag.grounding_validator import GroundingValidator, GroundingValidationResult
from app.core.config import settings
from app.core.logging import logger


class RAGQueryInput(BaseModel):
    query: str = Field(..., example="Why are my chilli leaves curling?")
    language: Optional[str] = Field(default=None, example="te")
    intent: Optional[str] = Field(default=None, example="CROP_SYMPTOM")
    crop: Optional[str] = Field(default=None, example="Chilli")
    crop_stage: Optional[str] = Field(default=None, example="flowering")
    location: Optional[Dict[str, Optional[str]]] = Field(default=None, example={"state": "Andhra Pradesh", "district": "Guntur"})
    state: Optional[str] = Field(default=None, example="Andhra Pradesh")
    district: Optional[str] = Field(default=None, example="Guntur")
    topic: Optional[str] = Field(default=None, example="disease")
    symptoms: Optional[List[str]] = Field(default=None, example=["leaf curling"])
    time_context: Optional[str] = Field(default=None, example="tomorrow_morning")
    top_k: int = Field(default=5, ge=1, le=20)
    farmer_context: Optional[Dict[str, Any]] = None


class RAGEvidenceOutput(BaseModel):
    query: str
    evidence_found: bool
    evidence_passages: List[str]
    citations: List[Citation]
    confidence: float
    grounded_summary: str
    verification_status: str = "verified"  # verified, RAG_LOW_RELEVANCE, RAG_NO_RESULTS, RAG_UNAVAILABLE
    authority_tier: str = "tier_1"
    parsed_language: str = "en"
    parsed_intent: str = "GENERAL_AGRICULTURE"
    parsed_crop: Optional[str] = None
    query_rewrites: List[str] = []
    retrieved_candidates_count: int = 0
    reranked_chunks: List[Dict[str, Any]] = []
    debug_trace: Optional[Dict[str, Any]] = None


class AgriculturalRAGService:
    _vector_store: Optional[VectorStore] = None
    _fallback_store: Optional[VectorStore] = None
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
                "id": "icar_chilli_thrips_01",
                "text": "For managing chilli leaf curl transmitted by whiteflies and thrips: Install yellow and blue sticky traps (15-20 per acre). Spray 10,000 ppm Azadirachtin (Neem oil) @ 2ml/litre during early vegetative stage. If nymph population crosses threshold (2 thrips/leaf), apply Fipronil 5% SC @ 2ml/litre. Maintain consistent irrigation to prevent water stress.",
                "metadata": {
                    "crop": "chilli",
                    "state": "andhra pradesh",
                    "district": "guntur",
                    "topic": "disease_management",
                    "subtopic": "leaf_curling",
                    "symptoms": ["leaf curling"],
                    "document": "ICAR-IIHR Package of Practices for Chilli",
                    "document_title": "ICAR-IIHR Package of Practices for Chilli",
                    "authority": "Indian Council of Agricultural Research (ICAR)",
                    "source": "Directorate of Plant Protection, Quarantine & Storage",
                    "source_authority": "tier_1",
                    "publication_date": "2024",
                    "section": "IPM Guidelines for Solanaceous Crops",
                    "url_or_ref": "https://iihr.res.in"
                }
            }
        ]

    @classmethod
    def _initialize_corpus(cls, force: bool = False):
        if cls._is_initialized and not force and cls._vector_store is not None:
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

        # Always initialize in-memory store
        mem_store = InMemoryVectorStore()
        mem_store.add_documents(chunks)
        cls._fallback_store = mem_store

        # Try Chroma vector store
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
        """
        Step 23: Multi-dimensional cache key preventing cross-intent cache pollution.
        """
        loc_str = ""
        if parsed.location:
            loc_str = f"{parsed.location.get('state')}_{parsed.location.get('district')}"
        return f"{parsed.language}:{parsed.intent}:{parsed.crop}:{loc_str}:{query_in.query.strip().lower()}"

    @classmethod
    def search(cls, query_in: RAGQueryInput) -> RAGEvidenceOutput:
        cls._initialize_corpus()

        # Step 3: Query Understanding & Normalization
        parsed = QueryUnderstandingService.understand(
            query=query_in.query,
            farmer_context=query_in.farmer_context
        )

        # Allow caller overrides if explicitly supplied in input
        if query_in.crop:
            parsed.crop = query_in.crop.strip().lower()
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

        # Step 23: Cache check
        cache_key = cls._generate_cache_key(query_in, parsed)
        if cache_key in cls._query_cache:
            cached_item = cls._query_cache[cache_key]
            # Verify cache entry is not stale (< 600s)
            if time.time() - cached_item.get("timestamp", 0) < 600:
                logger.debug(f"RAG query cache hit for key: {cache_key}")
                return cached_item["output"]

        # Step 4: Controlled Query Rewriting
        search_queries = QueryRewriter.rewrite(parsed)

        # Step 7: Hybrid Candidate Retrieval across all query rewrites
        candidate_map: Dict[str, SearchResult] = {}
        for sq in search_queries:
            sq_emb = cls._embed_text(sq)
            
            # Primary search in active store
            results = cls._vector_store.search(
                query_embedding=sq_emb,
                top_k=15,
                query_text=sq
            )

            # Fallback store if primary returned nothing
            if not results and cls._fallback_store:
                results = cls._fallback_store.search(
                    query_embedding=sq_emb,
                    top_k=15,
                    query_text=sq
                )

            for r in results:
                cid = r.chunk.chunk_id
                if cid not in candidate_map or r.similarity_score > candidate_map[cid].similarity_score:
                    candidate_map[cid] = r

        candidate_list = list(candidate_map.values())

        if not candidate_list:
            out = RAGEvidenceOutput(
                query=query_in.query,
                evidence_found=False,
                evidence_passages=[],
                citations=[],
                confidence=0.0,
                grounded_summary="No verified agricultural research documentation found matching this specific query.",
                verification_status="RAG_NO_RESULTS",
                parsed_language=parsed.language,
                parsed_intent=parsed.intent,
                parsed_crop=parsed.crop,
                query_rewrites=search_queries,
                retrieved_candidates_count=0,
                reranked_chunks=[]
            )
            return out

        # Step 12 & 13: 2-Stage Reranking & Relevance Thresholding
        reranked_chunks: List[RerankedChunk] = AgriculturalReranker.rerank(
            candidates=candidate_list,
            query_info=parsed,
            top_k=query_in.top_k,
            min_threshold=AgriculturalReranker.MIN_RELEVANCE_THRESHOLD
        )

        if not reranked_chunks:
            # All candidates scored below relevance threshold
            out = RAGEvidenceOutput(
                query=query_in.query,
                evidence_found=False,
                evidence_passages=[],
                citations=[],
                confidence=0.0,
                grounded_summary="No verified agricultural research documentation found matching this specific query with sufficient relevance.",
                verification_status="RAG_LOW_RELEVANCE",
                parsed_language=parsed.language,
                parsed_intent=parsed.intent,
                parsed_crop=parsed.crop,
                query_rewrites=search_queries,
                retrieved_candidates_count=len(candidate_list),
                reranked_chunks=[]
            )
            return out

        # Extract verified passages and metadata for citations
        verified_passages = [rc.content for rc in reranked_chunks]
        verified_metas = [rc.metadata for rc in reranked_chunks]
        citations = CitationBuilder.build_citations(verified_metas)

        # Grounded confidence calculation
        avg_score = sum(rc.rerank_score for rc in reranked_chunks) / len(reranked_chunks)
        confidence = round(min(0.99, max(0.65, avg_score)), 2)

        # Primary summary passage
        summary = verified_passages[0] if verified_passages else ""

        out = RAGEvidenceOutput(
            query=query_in.query,
            evidence_found=True,
            evidence_passages=verified_passages,
            citations=citations,
            confidence=confidence,
            grounded_summary=summary,
            verification_status="verified",
            authority_tier=reranked_chunks[0].metadata.get("source_authority", "tier_1"),
            parsed_language=parsed.language,
            parsed_intent=parsed.intent,
            parsed_crop=parsed.crop,
            query_rewrites=search_queries,
            retrieved_candidates_count=len(candidate_list),
            reranked_chunks=[rc.model_dump() for rc in reranked_chunks]
        )

        # Record in query cache
        cls._query_cache[cache_key] = {
            "timestamp": time.time(),
            "output": out
        }

        return out

    @classmethod
    def search_debug(cls, query_in: RAGQueryInput) -> Dict[str, Any]:
        """
        Step 25: RAG Debug Mode. Returns complete inspection trace.
        """
        cls._initialize_corpus()

        parsed = QueryUnderstandingService.understand(
            query=query_in.query,
            farmer_context=query_in.farmer_context
        )
        if query_in.crop:
            parsed.crop = query_in.crop.strip().lower()
        if query_in.language:
            parsed.language = query_in.language.strip().lower()

        rewrites = QueryRewriter.rewrite(parsed)

        candidate_map: Dict[str, SearchResult] = {}
        for sq in rewrites:
            sq_emb = cls._embed_text(sq)
            results = cls._vector_store.search(
                query_embedding=sq_emb,
                top_k=15,
                query_text=sq
            )
            for r in results:
                cid = r.chunk.chunk_id
                if cid not in candidate_map or r.similarity_score > candidate_map[cid].similarity_score:
                    candidate_map[cid] = r

        candidate_list = list(candidate_map.values())
        reranked_chunks = AgriculturalReranker.rerank(
            candidates=candidate_list,
            query_info=parsed,
            top_k=query_in.top_k,
            min_threshold=0.0  # Show all for debug inspection
        )

        accepted = [rc for rc in reranked_chunks if rc.rejection_reason is None]
        rejected = [rc for rc in reranked_chunks if rc.rejection_reason is not None]

        # Context Object
        ctx = ContextBuilder.build_context(
            query_info=parsed,
            reranked_chunks=accepted[:query_in.top_k],
            farm_state=query_in.farmer_context
        )
        llm_prompt = ContextBuilder.format_llm_prompt(ctx)

        return {
            "request": {
                "query": query_in.query,
                "language": parsed.language,
                "intent": parsed.intent,
                "crop": parsed.crop,
                "symptoms": parsed.symptoms,
                "location": parsed.location
            },
            "query_rewrites": rewrites,
            "retrieval": {
                "candidate_count": len(candidate_list)
            },
            "accepted_evidence": [
                {
                    "chunk_id": rc.chunk_id,
                    "title": rc.metadata.get("document_title"),
                    "authority": rc.metadata.get("source"),
                    "rerank_score": rc.rerank_score,
                    "crop": rc.metadata.get("crop"),
                    "topic": rc.metadata.get("topic")
                }
                for rc in accepted[:query_in.top_k]
            ],
            "rejected_evidence": [
                {
                    "chunk_id": rc.chunk_id,
                    "rerank_score": rc.rerank_score,
                    "rejection_reason": rc.rejection_reason
                }
                for rc in rejected[:5]
            ],
            "llm_context_preview": llm_prompt[:500] + "...",
            "status": "RAG_SUCCESS" if accepted else "RAG_LOW_RELEVANCE"
        }
