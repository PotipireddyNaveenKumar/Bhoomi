from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import math
import os
import re
from app.core.logging import logger
from app.core.config import settings

class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: Dict[str, Any]  # crop, state, district, language, topic, source, authority, publication_date
    embedding: Optional[List[float]] = None

class SearchResult(BaseModel):
    chunk: DocumentChunk
    similarity_score: float

class VectorStore(ABC):
    @abstractmethod
    def add_documents(self, chunks: List[DocumentChunk]):
        pass

    @abstractmethod
    def search(self, query_embedding: List[float], top_k: int = 3, filter_criteria: Optional[Dict[str, Any]] = None, query_text: Optional[str] = None) -> List[SearchResult]:
        pass

class InMemoryVectorStore(VectorStore):
    """
    High-performance in-memory vector store with cosine similarity, BM25 fallback, and metadata filtering.
    """
    def __init__(self):
        self._chunks: List[DocumentChunk] = []

    def add_documents(self, chunks: List[DocumentChunk]):
        self._chunks.extend(chunks)

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query_embedding: List[float], top_k: int = 3, filter_criteria: Optional[Dict[str, Any]] = None, query_text: Optional[str] = None) -> List[SearchResult]:
        scored: List[SearchResult] = []

        for chunk in self._chunks:
            # Metadata filter check
            if filter_criteria:
                match = True
                for k, v in filter_criteria.items():
                    if k in chunk.metadata and chunk.metadata[k].lower() != str(v).lower():
                        match = False
                        break
                if not match:
                    continue

            if chunk.embedding and query_embedding:
                score = self._cosine_similarity(query_embedding, chunk.embedding)
            else:
                score = 0.5

            # Hybrid keyword boost if query_text given
            if query_text:
                q_tokens = set(re.findall(r'\w+', query_text.lower()))
                c_tokens = set(re.findall(r'\w+', chunk.content.lower()))
                common = q_tokens.intersection(c_tokens)
                if common:
                    score = min(1.0, score + 0.15 * min(3, len(common)))

            scored.append(SearchResult(chunk=chunk, similarity_score=round(score, 4)))

        scored.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored[:top_k]


class ChromaVectorStore(VectorStore):
    """
    Production ChromaDB persistent vector store.
    Stores knowledge collections under data/chroma with cosine distance indexing.
    """
    def __init__(self, persist_dir: Optional[str] = None, collection_name: str = "bhoomi_agri_kb"):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        os.makedirs(self.persist_dir, exist_ok=True)
        import chromadb
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self._chunks_map: Dict[str, DocumentChunk] = {}

    def add_documents(self, chunks: List[DocumentChunk]):
        if not chunks:
            return

        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for c in chunks:
            ids.append(c.chunk_id)
            documents.append(c.content)
            self._chunks_map[c.chunk_id] = c
            
            # Sanitize metadata for Chroma (strings, ints, floats, bools only)
            clean_meta = {}
            for k, v in c.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                elif isinstance(v, list):
                    clean_meta[k] = ", ".join(str(item) for item in v)
                else:
                    clean_meta[k] = str(v)
            metadatas.append(clean_meta)

            if c.embedding:
                embeddings.append(c.embedding)

        kwargs: Dict[str, Any] = {
            "ids": ids,
            "documents": documents,
            "metadatas": metadatas
        }
        if len(embeddings) == len(ids):
            kwargs["embeddings"] = embeddings

        try:
            self.collection.upsert(**kwargs)
        except Exception as e:
            if "dimension" in str(e).lower():
                logger.warning(f"Chroma collection dimension mismatch ({e}); recreating collection with new embedding dimension.")
                self.client.delete_collection(self.collection.name)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection.name,
                    metadata={"hnsw:space": "cosine"}
                )
                self.collection.upsert(**kwargs)
            else:
                raise e

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 3,
        filter_criteria: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None
    ) -> List[SearchResult]:
        where_filter = None
        if filter_criteria:
            if len(filter_criteria) == 1:
                k, v = list(filter_criteria.items())[0]
                where_filter = {k: {"$eq": str(v).lower()}}
            else:
                where_filter = {"$and": [{k: {"$eq": str(v).lower()}} for k, v in filter_criteria.items()]}

        try:
            query_kwargs: Dict[str, Any] = {
                "n_results": min(top_k, max(1, self.collection.count())),
                "where": where_filter
            }
            if query_embedding:
                query_kwargs["query_embeddings"] = [query_embedding]
            elif query_text:
                query_kwargs["query_texts"] = [query_text]

            results = self.collection.query(**query_kwargs)
        except Exception as e:
            logger.warning(f"Chroma query with filter {where_filter} failed ({e}); falling back without filter")
            query_kwargs["where"] = None
            results = self.collection.query(**query_kwargs)

        scored: List[SearchResult] = []
        if results and results.get("ids") and len(results["ids"]) > 0:
            res_ids = results["ids"][0]
            res_docs = results["documents"][0] if results.get("documents") else []
            res_metas = results["metadatas"][0] if results.get("metadatas") else []
            res_dists = results["distances"][0] if results.get("distances") else []

            for i, chunk_id in enumerate(res_ids):
                # Convert cosine distance to similarity score
                dist = res_dists[i] if i < len(res_dists) else 0.5
                sim = round(max(0.0, min(1.0, 1.0 - dist)), 4)
                
                content = res_docs[i] if i < len(res_docs) else ""
                meta = res_metas[i] if i < len(res_metas) else {}

                chunk = self._chunks_map.get(chunk_id, DocumentChunk(
                    chunk_id=chunk_id,
                    content=content,
                    metadata=meta,
                    embedding=None
                ))
                scored.append(SearchResult(chunk=chunk, similarity_score=sim))

        return scored
