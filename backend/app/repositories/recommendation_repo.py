from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, desc
from app.models.recommendation_trace import RecommendationTrace
from app.core.datetime_utils import utc_now_naive


class RecommendationRepository:
    """
    Authoritative repository for persistent recommendation and decision traces.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_trace(
        self,
        decision_id: str,
        farmer_id: str,
        recommendation_text: str,
        farm_id: Optional[str] = None,
        recommendation_id: Optional[str] = None,
        intent: Optional[str] = None,
        decision_type: Optional[str] = None,
        confidence: float = 1.0,
        input_context: Optional[Dict[str, Any]] = None,
        data_freshness: Optional[Dict[str, str]] = None,
        tools_used: Optional[List[str]] = None,
        model_versions: Optional[Dict[str, str]] = None,
        rag_sources: Optional[List[str]] = None,
        weather_source: Optional[str] = None,
        market_source: Optional[str] = None,
        calculations: Optional[Dict[str, Any]] = None,
        safety_checks: Optional[List[str]] = None,
        assumptions: Optional[List[str]] = None,
        rationale: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        xai_info: Optional[Dict[str, Any]] = None,
        farmer_action: str = "PENDING",
        outcome: Optional[str] = None,
        feedback_rating: Optional[str] = None,
        feedback_notes: Optional[str] = None,
        locale: str = "en",
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> RecommendationTrace:
        rec_id = recommendation_id or decision_id

        # Idempotency guard: avoid duplicate write if decision_id already exists
        existing = await self.get_by_decision_id(decision_id)
        if existing:
            return existing

        trace = RecommendationTrace(
            decision_id=decision_id,
            recommendation_id=rec_id,
            farmer_id=farmer_id,
            farm_id=farm_id,
            intent=intent or decision_type,
            decision_type=decision_type or intent,
            recommendation_text=recommendation_text,
            confidence=confidence,
            input_context=input_context or {},
            data_freshness=data_freshness or {},
            tools_used=tools_used or [],
            model_versions=model_versions or {},
            rag_sources=rag_sources or [],
            weather_source=weather_source,
            market_source=market_source,
            calculations=calculations or {},
            safety_checks=safety_checks or [],
            assumptions=assumptions or [],
            rationale=rationale or (assumptions[0] if assumptions else None),
            evidence=evidence or {},
            xai_info=xai_info or {},
            farmer_action=farmer_action or "PENDING",
            outcome=outcome,
            feedback_rating=feedback_rating,
            feedback_notes=feedback_notes,
            locale=locale or "en",
            metadata_json=metadata_json or {},
        )
        self.db.add(trace)
        await self.db.commit()
        await self.db.refresh(trace)
        return trace

    async def get_by_decision_id(self, decision_id: str) -> Optional[RecommendationTrace]:
        query = select(RecommendationTrace).where(
            or_(
                RecommendationTrace.decision_id == decision_id,
                RecommendationTrace.recommendation_id == decision_id,
                RecommendationTrace.id == decision_id,
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_for_farmer(
        self,
        farmer_id: str,
        farm_id: Optional[str] = None,
        decision_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RecommendationTrace]:
        query = select(RecommendationTrace).where(RecommendationTrace.farmer_id == farmer_id)
        if farm_id:
            query = query.where(RecommendationTrace.farm_id == farm_id)
        if decision_type:
            query = query.where(RecommendationTrace.decision_type == decision_type)
        query = query.order_by(desc(RecommendationTrace.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_for_farm(
        self,
        farm_id: str,
        farmer_id: Optional[str] = None,
        decision_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[RecommendationTrace]:
        query = select(RecommendationTrace).where(RecommendationTrace.farm_id == farm_id)
        if farmer_id:
            query = query.where(RecommendationTrace.farmer_id == farmer_id)
        if decision_type:
            query = query.where(RecommendationTrace.decision_type == decision_type)
        query = query.order_by(desc(RecommendationTrace.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_feedback(
        self,
        decision_id: str,
        farmer_action: str,
        feedback_rating: Optional[str] = None,
        feedback_notes: Optional[str] = None,
    ) -> Optional[RecommendationTrace]:
        trace = await self.get_by_decision_id(decision_id)
        if not trace:
            return None
        trace.farmer_action = farmer_action
        if feedback_rating is not None:
            trace.feedback_rating = feedback_rating
        if feedback_notes is not None:
            trace.feedback_notes = feedback_notes
        trace.updated_at = utc_now_naive()
        await self.db.commit()
        await self.db.refresh(trace)
        return trace
