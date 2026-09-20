import math
import re
from typing import List, Dict, Any, Optional, Set
from collections import Counter
from app.services.rag.vector_store import DocumentChunk, SearchResult
from app.core.logging import logger


class BM25Retriever:
    """
    In-memory BM25Okapi lexical retrieval engine for BHOOMI RAG 2.0.
    Indexes agricultural knowledge documents with Indic and English tokenization.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[DocumentChunk] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.corpus_size: int = 0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.tokenized_docs: List[List[str]] = []

    STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
        "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
        "can", "cannot", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for",
        "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
        "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just", "me", "more",
        "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other",
        "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so", "some", "such",
        "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they",
        "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "we", "were", "what",
        "when", "where", "which", "while", "who", "whom", "why", "with", "would", "you", "your", "yours",
        "yourself", "yourselves", "term", "without", "random", "completely", "non", "existent", "tell", "give", "please"
    }

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """
        Multilingual tokenizer supporting Latin and Indic alphabets (Telugu, Hindi, Tamil, Kannada, Malayalam).
        """
        if not text:
            return []
        tokens = re.findall(r'[\w\u0900-\u097F\u0C00-\u0C7F\u0B80-\u0BFF\u0C80-\u0CFF\u0D00-\u0D7F]+', text.lower())
        return [t for t in tokens if len(t) >= 2 and t not in cls.STOP_WORDS]

    def index_documents(self, chunks: List[DocumentChunk]):
        """
        Builds the inverted index, doc lengths, and IDF tables.
        """
        self.chunks = list(chunks)
        self.corpus_size = len(chunks)
        if self.corpus_size == 0:
            self.avg_doc_len = 0.0
            return

        self.tokenized_docs = []
        self.doc_lengths = []
        self.doc_freqs = Counter()

        total_tokens = 0
        for chunk in chunks:
            meta_blob = " ".join([
                str(chunk.metadata.get("keywords", "")),
                str(chunk.metadata.get("crop", "")),
                str(chunk.metadata.get("topic", "")),
                str(chunk.metadata.get("subtopic", "")),
                str(chunk.metadata.get("disease", "")),
                str(chunk.metadata.get("pest", "")),
                str(chunk.metadata.get("symptoms", ""))
            ])
            full_text = f"{chunk.content} {meta_blob}"
            tokens = self.tokenize(full_text)
            self.tokenized_docs.append(tokens)
            doc_len = len(tokens)
            self.doc_lengths.append(doc_len)
            total_tokens += doc_len

            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.doc_freqs[t] += 1

        self.avg_doc_len = total_tokens / self.corpus_size

        # Precompute IDF
        self.idf = {}
        for token, freq in self.doc_freqs.items():
            # BM25Okapi IDF with smoothing
            self.idf[token] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

        logger.info(f"BM25 index built with {self.corpus_size} documents, {len(self.idf)} unique vocabulary terms.")

    def search(
        self,
        query_text: str,
        top_k: int = 15,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        if not query_text or self.corpus_size == 0:
            return []

        q_tokens = self.tokenize(query_text)
        if not q_tokens:
            return []

        scores: List[tuple[int, float, int]] = []

        for idx, doc_tokens in enumerate(self.tokenized_docs):
            chunk = self.chunks[idx]

            # Metadata filter check
            if filter_criteria:
                match = True
                for k, v in filter_criteria.items():
                    if k in chunk.metadata and chunk.metadata[k] is not None:
                        if str(chunk.metadata[k]).lower() != str(v).lower():
                            match = False
                            break
                if not match:
                    continue

            # Compute BM25 score
            doc_len = self.doc_lengths[idx]
            token_counts = Counter(doc_tokens)
            doc_score = 0.0
            matched_count = 0

            for q_term in q_tokens:
                if q_term not in self.idf:
                    continue
                tf = token_counts.get(q_term, 0)
                if tf == 0:
                    continue
                matched_count += 1
                idf = self.idf[q_term]
                num = tf * (self.k1 + 1.0)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / max(1.0, self.avg_doc_len)))
                doc_score += idf * (num / denom)

            if doc_score > 0 and matched_count > 0:
                scores.append((idx, doc_score, matched_count))

        if not scores:
            return []

        scores.sort(key=lambda x: x[1], reverse=True)
        max_score = max(s[1] for s in scores)
        if max_score <= 0:
            max_score = 1.0

        results: List[SearchResult] = []
        for idx, raw_score, matched in scores[:top_k]:
            coverage = matched / max(1, len(q_tokens))
            # Calibrate: scaled by max_score and query token coverage
            normalized_score = round(min(1.0, (raw_score / max(max_score, 3.5)) * 0.75 + coverage * 0.25), 4)
            results.append(SearchResult(
                chunk=self.chunks[idx],
                similarity_score=normalized_score,
                retrieval_method="lexical_bm25"
            ))

        return results
