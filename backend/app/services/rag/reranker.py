"""
2-Stage Agricultural Knowledge Reranker for BHOOMI RAG.
Reranks candidate evidence chunks using a multi-dimensional objective function:
- Query Semantic & Lexical Relevance
- Crop Priority & Specificity (Step 8: crop-specific queries strictly prefer crop-specific docs)
- Topic Priority & Symptom Match (Step 9: symptom queries reject market/unrelated docs)
- Location Relevance (Step 10: regional preference without discarding national ICAR)
- Source Authority Tiering (Step 11: ICAR / SAUs > general extension)
- Configurable Relevance Thresholding (Step 13: MIN_RELEVANCE_THRESHOLD = 0.50)
"""
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.rag.vector_store import SearchResult, DocumentChunk
from app.services.rag.query_understanding import QueryUnderstandingResult
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
    rejection_reason: Optional[str] = None


class AgriculturalReranker:
    """
    Production 2-stage reranker for agricultural decision intelligence.
    """

    DEFAULT_WEIGHTS = {
        "semantic_weight": 0.35,
        "keyword_weight": 0.20,
        "crop_weight": 0.20,
        "topic_weight": 0.15,
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
        matches = 0
        total = max(1, len(query_terms))
        for term in query_terms:
            t_clean = term.strip().lower()
            if len(t_clean) < 3:
                continue
            if t_clean in full_doc:
                matches += 1

        return min(1.0, round(matches / max(1, min(total, 6)), 3))

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
        target_loc = query_info.location or {}
        target_state = (target_loc.get("state") or "").strip().lower()
        target_district = (target_loc.get("district") or "").strip().lower()

        # Build query token set for lexical matching
        q_tokens = set(re.findall(r'\w+', query_info.normalized_query.lower()))
        for sym in target_symptoms:
            q_tokens.update(sym.split("_"))
        if target_crop:
            q_tokens.add(target_crop)
        if target_pest:
            q_tokens.add(target_pest)

        reranked_list: List[RerankedChunk] = []

        for candidate in candidates:
            chunk = candidate.chunk
            meta = chunk.metadata or {}
            content = chunk.content

            chunk_crop = str(meta.get("crop", "general")).strip().lower()
            chunk_topic = str(meta.get("topic", "agronomy")).strip().lower()
            chunk_subtopic = str(meta.get("subtopic", "")).strip().lower()
            chunk_symptoms = [str(s).lower() for s in (meta.get("symptoms") or [])]
            chunk_pest = str(meta.get("pest", "") or "").lower()
            chunk_disease = str(meta.get("disease", "") or "").lower()
            chunk_state = str(meta.get("state", "all_india")).strip().lower()
            chunk_district = str(meta.get("district", "all")).strip().lower()
            chunk_authority = str(meta.get("source_authority", "tier_1")).strip().lower()

            # 1. Semantic Score from vector retrieval
            sem_score = candidate.similarity_score

            # 2. Keyword & Lexical Overlap Score
            kw_score = cls._compute_keyword_overlap(list(q_tokens), content, meta)

            # 3. Crop Relevance (Step 8: Crop Priority)
            crop_score = 0.50
            crop_penalty = 1.0
            if target_crop:
                if chunk_crop == target_crop:
                    crop_score = 1.00
                elif chunk_crop in ["general", "all"]:
                    crop_score = 0.60
                else:
                    # Mismatched crop penalty! (e.g. query is chilli, doc is tomato/rice)
                    crop_score = 0.10
                    crop_penalty = 0.35  # Heavy penalty so wrong crop cannot outrank
            else:
                crop_score = 0.80 if chunk_crop in ["general", "all"] else 0.50

            # 4. Topic Relevance (Step 9: Topic Priority)
            topic_score = 0.50
            topic_penalty = 1.0
            is_symptom_inquiry = target_intent in ["CROP_SYMPTOM", "PEST_QUERY", "DISEASE_QUERY"] or bool(target_symptoms)

            if is_symptom_inquiry:
                if any(t in chunk_topic for t in ["disease", "pest", "symptom"]):
                    topic_score = 0.90
                    # Check for symptom match (e.g. leaf_curling)
                    for sym in target_symptoms:
                        if any(sym in s for s in chunk_symptoms) or sym in chunk_subtopic or sym in content.lower():
                            topic_score = 1.00
                            break
                    if target_pest and (target_pest in chunk_pest or target_pest in content.lower()):
                        topic_score = 1.00
                elif "irrigation" in chunk_topic or "water" in chunk_subtopic:
                    # Water stress can be a supporting cause of leaf curling, but lower than primary disease
                    topic_score = 0.70
                elif any(m in chunk_topic for m in ["market", "economics", "scheme"]):
                    # Step 9 strict rule: A document about 'market price' should NOT be retrieved for leaf curl!
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

            # 5. Location Relevance (Step 10)
            loc_score = 0.60
            if target_district and chunk_district != "all":
                if target_district in chunk_district or chunk_district in target_district:
                    loc_score = 1.00
            elif target_state and chunk_state != "all_india":
                if target_state in chunk_state or chunk_state in target_state:
                    loc_score = 0.85
            else:
                loc_score = 0.70 if chunk_state == "all_india" else 0.50

            # 6. Authority Tier Score (Step 11)
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

            # Apply hard mismatch penalties
            composite = round(composite * crop_penalty * topic_penalty, 4)

            # Check rejection reasons
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
                rejection_reason=rejection_reason
            ))

        # Sort descending by rerank_score
        reranked_list.sort(key=lambda x: x.rerank_score, reverse=True)

        # Filter out rejected chunks from top evidence return
        accepted = [c for c in reranked_list if c.rejection_reason is None]
        return accepted[:top_k]
