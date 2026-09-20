"""
2-Stage Agricultural Knowledge Reranker for BHOOMI RAG 2.0.
Reranks candidate evidence chunks using a multi-dimensional objective function:
- Query Semantic & Lexical Relevance (Vector + BM25)
- Crop Priority & Specificity (crop-specific queries strictly prefer crop-specific docs)
- Crop Stage Affinity (phenological stage match: vegetative, flowering, fruiting, harvest)
- Topic Priority & Symptom Match (symptom queries reject market/unrelated docs)
- Location Relevance (regional preference without discarding national ICAR)
- Source Authority Tiering (ICAR / SAUs > general extension)
- Configurable Relevance Thresholding (MIN_RELEVANCE_THRESHOLD = 0.50)
"""
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.rag.vector_store import SearchResult, DocumentChunk
from app.services.rag.query_understanding import QueryUnderstandingResult
from app.services.rag.evidence_model import CanonicalEvidenceItem, AuthorityTier
from app.core.logging import logger


class RerankedChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    retrieval_score: float
    rerank_score: float
    query_relevance: float
    crop_relevance: float
    topic_relevance: float
    location_relevance: float
    authority_score: float
    stage_relevance: float = 0.50
    retrieval_method: str = "hybrid"
    rejection_reason: Optional[str] = None

    def to_canonical_evidence(self) -> CanonicalEvidenceItem:
        meta = self.metadata or {}
        tier = meta.get("source_authority", "tier_1")
        if tier == "tier_1":
            auth_level = AuthorityTier.TIER_1_GOVT_ICAR.value
        elif tier == "tier_2":
            auth_level = AuthorityTier.TIER_2_AGRI_UNIVERSITY.value
        elif tier == "tier_3":
            auth_level = AuthorityTier.TIER_3_COMMODITY_BOARD.value
        elif tier == "tier_4":
            auth_level = AuthorityTier.TIER_4_GENERAL.value
        else:
            auth_level = str(tier)

        doc_id = meta.get("id") or meta.get("chunk_id") or self.chunk_id
        doc_title = meta.get("document_title") or meta.get("document") or f"Agricultural Reference {doc_id}"

        return CanonicalEvidenceItem(
            chunk_id=self.chunk_id,
            document_id=str(doc_id),
            title=doc_title,
            source=meta.get("source") or meta.get("authority") or "Agricultural Extension",
            source_url=meta.get("source_url") or meta.get("url_or_ref"),
            crop=meta.get("crop"),
            crop_stage=meta.get("crop_stage"),
            topic=meta.get("topic"),
            state=meta.get("state"),
            district=meta.get("district"),
            language=meta.get("language") or "en",
            source_date=str(meta.get("publication_date") or meta.get("source_date") or "2024"),
            authority_level=auth_level,
            section=meta.get("section") or "General Agronomic Advisory",
            content=self.content,
            relevance_score=self.rerank_score,
            retrieval_method=self.retrieval_method
        )


class AgriculturalReranker:
    """
    Production 2-stage reranker for agricultural decision intelligence.
    """

    DEFAULT_WEIGHTS = {
        "semantic_weight": 0.35,
        "keyword_weight": 0.25,
        "crop_weight": 0.20,
        "topic_weight": 0.10,
        "location_weight": 0.05,
        "authority_weight": 0.05
    }

    MIN_RELEVANCE_THRESHOLD = 0.50

    AUTHORITY_TIER_SCORES = {
        "tier_1": 1.00,   # ICAR, DPPQS, IMD, AGMARKNET, DA&FW, CIBRC
        "tier_2": 0.85,   # ANGRAU, TNAU, PJTSAU, State Agri Depts, KVKs
        "tier_3": 0.65,   # Commodity boards, National boards
        "tier_4": 0.45    # General portals
    }

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
        "yourself", "yourselves", "term", "without", "random", "completely", "non", "existent", "tell", "give", "please",
        "information", "details", "help", "want", "need", "asking"
    }

    @classmethod
    def _compute_keyword_overlap(cls, query_terms: List[str], chunk_text: str, chunk_meta: Dict[str, Any]) -> float:
        content_lower = chunk_text.lower()
        meta_blob = " ".join([
            str(chunk_meta.get("keywords", "")),
            str(chunk_meta.get("crop", "")),
            str(chunk_meta.get("topic", "")),
            str(chunk_meta.get("subtopic", "")),
            str(chunk_meta.get("disease", "")),
            str(chunk_meta.get("pest", "")),
            str(chunk_meta.get("symptoms", ""))
        ]).lower()

        full_doc = f"{content_lower} {meta_blob}"
        clean_terms = [t.strip().lower() for t in query_terms if t.strip().lower() not in cls.STOP_WORDS and len(t.strip()) >= 3]
        if not clean_terms:
            return 0.0

        matches = 0
        for term in clean_terms:
            if term in full_doc:
                matches += 1

        return min(1.0, round(matches / len(clean_terms), 3))

    @classmethod
    def rerank(
        cls,
        candidates: List[SearchResult],
        query_info: QueryUnderstandingResult,
        top_k: int = 5,
        weights: Optional[Dict[str, float]] = None,
        min_threshold: Optional[float] = None
    ) -> List[RerankedChunk]:
        if not candidates:
            return []

        w = dict(cls.DEFAULT_WEIGHTS)
        if weights:
            w.update(weights)

        threshold = min_threshold if min_threshold is not None else cls.MIN_RELEVANCE_THRESHOLD
        target_crop = (query_info.crop or "").strip().lower()
        target_intent = query_info.intent.upper()
        target_symptoms = [s.lower() for s in query_info.symptoms]
        target_pest = (query_info.pest or "").lower()
        target_stage = (query_info.growth_stage or "").strip().lower()
        target_loc = query_info.location or {}
        target_state = (target_loc.get("state") or "").strip().lower()
        target_district = (target_loc.get("district") or "").strip().lower()

        # Build query token set for lexical matching including translated entities
        q_tokens = set(re.findall(r'[\w\u0900-\u097F\u0C00-\u0C7F\u0B80-\u0BFF\u0C80-\u0CFF\u0D00-\u0D7F]+', query_info.normalized_query.lower()))
        for sym in target_symptoms:
            for part in sym.split("_"):
                if len(part) >= 3:
                    q_tokens.add(part)
        if target_crop:
            q_tokens.add(target_crop)
        if target_pest:
            for part in target_pest.split():
                if len(part) >= 3:
                    q_tokens.add(part)

        reranked_list: List[RerankedChunk] = []

        for candidate in candidates:
            chunk = candidate.chunk
            meta = chunk.metadata or {}
            content = chunk.content

            chunk_crop = str(meta.get("crop", "general")).strip().lower()
            chunk_stage = str(meta.get("crop_stage", "all")).strip().lower()
            chunk_topic = str(meta.get("topic", "agronomy")).strip().lower()
            chunk_subtopic = str(meta.get("subtopic", "")).strip().lower()
            chunk_symptoms = [str(s).lower() for s in (meta.get("symptoms") or [])]
            chunk_pest = str(meta.get("pest", "") or "").lower()
            chunk_disease = str(meta.get("disease", "") or "").lower()
            chunk_state = str(meta.get("state", "all_india")).strip().lower()
            chunk_district = str(meta.get("district", "all")).strip().lower()
            chunk_authority = str(meta.get("source_authority", "tier_1")).strip().lower()

            # 1. Semantic/retrieval Score
            sem_score = candidate.similarity_score

            # 2. Keyword & Lexical Overlap Score
            kw_score = cls._compute_keyword_overlap(list(q_tokens), content, meta)

            # 3. Crop Relevance (Crop Priority)
            crop_score = 0.50
            crop_penalty = 1.0
            if target_crop:
                meta_blob = f"{chunk_crop} {chunk_topic} {chunk_subtopic} {content.lower()}"
                if chunk_crop == target_crop or target_crop in chunk_crop:
                    crop_score = 1.00
                elif target_crop in content.lower() or target_crop in meta_blob:
                    crop_score = 0.85
                elif chunk_crop in ["general", "all"]:
                    crop_score = 0.35
                    crop_penalty = 0.55
                else:
                    crop_score = 0.05
                    crop_penalty = 0.20
            else:
                crop_score = 0.80 if chunk_crop in ["general", "all"] else 0.50

            # 3b. Crop Stage Relevance
            stage_score = 0.50
            stage_penalty = 1.0
            if target_stage:
                if chunk_stage == target_stage or target_stage in chunk_stage:
                    stage_score = 1.00
                elif chunk_stage in ["all", "general"]:
                    stage_score = 0.70
                else:
                    stage_score = 0.20
                    stage_penalty = 0.60

            # 4. Topic Relevance (Topic Priority)
            topic_score = 0.50
            topic_penalty = 1.0
            is_symptom_inquiry = target_intent in ["CROP_SYMPTOM", "PEST_QUERY", "DISEASE_QUERY"] or bool(target_symptoms)

            if is_symptom_inquiry:
                if any(t in chunk_topic for t in ["disease", "pest", "symptom"]):
                    topic_score = 0.90
                    for sym in target_symptoms:
                        if any(sym in s for s in chunk_symptoms) or sym in chunk_subtopic or sym in content.lower():
                            topic_score = 1.00
                            break
                    if target_pest and (target_pest in chunk_pest or target_pest in content.lower()):
                        topic_score = 1.00
                elif "irrigation" in chunk_topic or "water" in chunk_subtopic:
                    topic_score = 0.70
                elif any(m in chunk_topic for m in ["market", "economics", "scheme"]):
                    topic_score = 0.05
                    topic_penalty = 0.10
                else:
                    topic_score = 0.40
            elif target_intent == "SPRAY_WEATHER_SAFETY":
                if "spray" in chunk_topic or "spray" in chunk_subtopic:
                    topic_score = 1.00
                elif "weather" in chunk_topic:
                    topic_score = 0.85
                else:
                    topic_score = 0.20
                    topic_penalty = 0.40
            elif target_intent == "IRRIGATION_QUERY":
                if "irrigation" in chunk_topic or "water" in chunk_subtopic:
                    topic_score = 1.00
                else:
                    topic_score = 0.30
            elif target_intent in ["PROFIT_SIMULATION", "ECONOMICS"]:
                if "economics" in chunk_topic or "profit" in chunk_subtopic or "cost" in chunk_subtopic:
                    topic_score = 1.00
                else:
                    topic_score = 0.30
            elif target_intent == "GOVERNMENT_SCHEME":
                if "scheme" in chunk_topic:
                    topic_score = 1.00
                else:
                    topic_score = 0.20
            elif target_intent == "SOIL_QUERY":
                if "soil" in chunk_topic:
                    topic_score = 1.00
                else:
                    topic_score = 0.30

            # 5. Location Relevance
            loc_score = 0.60
            if target_district and chunk_district != "all":
                if target_district in chunk_district or chunk_district in target_district:
                    loc_score = 1.00
            elif target_state and chunk_state != "all_india":
                if target_state in chunk_state or chunk_state in target_state:
                    loc_score = 0.85
            else:
                loc_score = 0.70 if chunk_state == "all_india" else 0.50

            # 6. Authority Tier Score
            auth_score = cls.AUTHORITY_TIER_SCORES.get(chunk_authority, 0.50)

            # Composite Rerank Score
            composite = (
                w["semantic_weight"] * sem_score
                + w["keyword_weight"] * kw_score
                + w["crop_weight"] * crop_score
                + w["topic_weight"] * topic_score
                + w["location_weight"] * loc_score
                + w["authority_weight"] * auth_score
            )

            # Apply hard penalties
            composite = round(composite * crop_penalty * topic_penalty * stage_penalty, 4)

            # Irrelevant query suppression: if query has zero keyword connection, suppress
            if kw_score == 0.0:
                composite = min(composite, 0.25)
            elif sem_score < 0.45 and kw_score < 0.20:
                composite = min(composite, 0.42)

            rejection_reason = None
            if composite < threshold:
                if crop_penalty < 0.5:
                    rejection_reason = f"crop mismatch (query crop '{target_crop}' vs chunk crop '{chunk_crop}')"
                elif topic_penalty < 0.5:
                    rejection_reason = f"topic mismatch (query intent '{target_intent}' vs chunk topic '{chunk_topic}')"
                else:
                    rejection_reason = f"score {composite:.2f} below threshold {threshold:.2f}"

            reranked_list.append(RerankedChunk(
                chunk_id=chunk.chunk_id,
                content=content,
                metadata=meta,
                retrieval_score=round(sem_score, 4),
                rerank_score=composite,
                query_relevance=round(kw_score, 4),
                crop_relevance=round(crop_score, 4),
                topic_relevance=round(topic_score, 4),
                location_relevance=round(loc_score, 4),
                authority_score=round(auth_score, 4),
                stage_relevance=round(stage_score, 4),
                retrieval_method=getattr(candidate, "retrieval_method", "hybrid"),
                rejection_reason=rejection_reason
            ))

        # Sort descending by rerank_score
        reranked_list.sort(key=lambda x: x.rerank_score, reverse=True)

        accepted = [c for c in reranked_list if c.rejection_reason is None]
        return accepted[:top_k]
