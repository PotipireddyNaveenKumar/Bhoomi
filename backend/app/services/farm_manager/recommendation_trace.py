import uuid
import asyncio
import logging
import concurrent.futures
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.recommendation_trace import RecommendationTrace
from app.repositories.recommendation_repo import RecommendationRepository

logger = logging.getLogger("bhoomi.recommendation_trace")


def _run_coroutine_sync(coro):
    """
    Executes an async coroutine synchronously.
    Handles both non-event-loop contexts (standard sync tests) and active event-loop
    contexts (sync functions called within async FastAPI endpoints).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        return asyncio.run(coro)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            def worker():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()

            future = executor.submit(worker)
            return future.result(timeout=15.0)


class FeedbackStatus:
    HELPFUL = "HELPFUL"
    NOT_HELPFUL = "NOT_HELPFUL"
    FOLLOWED = "FOLLOWED"
    NOT_FOLLOWED = "NOT_FOLLOWED"
    SUCCESSFUL = "SUCCESSFUL"
    UNSUCCESSFUL = "UNSUCCESSFUL"
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    # Legacy aliases
    USEFUL = "USEFUL"
    PARTIAL = "PARTIAL"
    NOT_USEFUL = "NOT_USEFUL"


class RecommendationRecord(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:10]}")
    farmer_id: str
    farm_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    intent: str
    decision_type: str = ""
    input_context: Dict[str, Any] = Field(default_factory=dict)
    data_freshness: Dict[str, str] = Field(default_factory=dict)
    tools_used: List[str] = Field(default_factory=list)
    model_versions: Dict[str, str] = Field(default_factory=dict)
    rag_sources: List[str] = Field(default_factory=list)
    weather_source: Optional[str] = None
    market_source: Optional[str] = None
    calculations: Dict[str, Any] = Field(default_factory=dict)
    safety_checks: List[str] = Field(default_factory=list)
    recommendation_text: str
    confidence: float
    assumptions: List[str] = Field(default_factory=list)
    farmer_action: str = "PENDING"  # ACCEPTED, MODIFIED, REJECTED, FOLLOWED, NOT_FOLLOWED, PENDING
    outcome: Optional[str] = None
    feedback_rating: Optional[str] = None  # HELPFUL, NOT_HELPFUL, SUCCESSFUL, UNSUCCESSFUL, CORRECT, INCORRECT
    feedback_notes: Optional[str] = None


def _trace_to_record(trace: RecommendationTrace) -> RecommendationRecord:
    return RecommendationRecord(
        recommendation_id=trace.recommendation_id or trace.decision_id,
        farmer_id=trace.farmer_id,
        farm_id=trace.farm_id or "",
        timestamp=trace.created_at.isoformat() if trace.created_at else datetime.now(timezone.utc).isoformat(),
        intent=trace.intent or trace.decision_type or "",
        decision_type=trace.decision_type or trace.intent or "",
        input_context=trace.input_context or {},
        data_freshness=trace.data_freshness or {},
        tools_used=trace.tools_used or [],
        model_versions=trace.model_versions or {},
        rag_sources=trace.rag_sources or [],
        weather_source=trace.weather_source,
        market_source=trace.market_source,
        calculations=trace.calculations or {},
        safety_checks=trace.safety_checks or [],
        recommendation_text=trace.recommendation_text,
        confidence=trace.confidence,
        assumptions=trace.assumptions or [],
        farmer_action=trace.farmer_action,
        outcome=trace.outcome,
        feedback_rating=trace.feedback_rating,
        feedback_notes=trace.feedback_notes,
    )


class RecommendationTraceStore:
    """
    Authoritative PostgreSQL-backed audit and explainability store for all high-impact AI farm decisions.
    Records full provenance and captures structured farmer feedback.
    """

    @classmethod
    async def record_trace_async(
        cls,
        record: RecommendationRecord,
        db: Optional[AsyncSession] = None
    ) -> RecommendationRecord:
        """Persists a recommendation trace to the authoritative SQL store asynchronously."""
        async def _execute(session: AsyncSession):
            repo = RecommendationRepository(session)
            trace = await repo.create_trace(
                decision_id=record.recommendation_id,
                farmer_id=record.farmer_id,
                recommendation_text=record.recommendation_text,
                farm_id=record.farm_id,
                recommendation_id=record.recommendation_id,
                intent=record.intent,
                decision_type=record.decision_type or record.intent,
                confidence=record.confidence,
                input_context=record.input_context,
                data_freshness=record.data_freshness,
                tools_used=record.tools_used,
                model_versions=record.model_versions,
                rag_sources=record.rag_sources,
                weather_source=record.weather_source,
                market_source=record.market_source,
                calculations=record.calculations,
                safety_checks=record.safety_checks,
                assumptions=record.assumptions,
                rationale=record.assumptions[0] if record.assumptions else None,
                farmer_action=record.farmer_action,
                outcome=record.outcome,
                feedback_rating=record.feedback_rating,
                feedback_notes=record.feedback_notes,
            )
            return _trace_to_record(trace)

        if db is not None:
            return await _execute(db)
        async with AsyncSessionLocal() as session:
            return await _execute(session)

    @classmethod
    def record_trace(cls, record: RecommendationRecord) -> RecommendationRecord:
        """Synchronous wrapper for legacy callers."""
        return _run_coroutine_sync(cls.record_trace_async(record))

    @classmethod
    async def get_trace_async(
        cls,
        recommendation_id: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[RecommendationRecord]:
        """Fetches a recommendation trace by recommendation_id/decision_id asynchronously."""
        async def _execute(session: AsyncSession):
            repo = RecommendationRepository(session)
            trace = await repo.get_by_decision_id(recommendation_id)
            return _trace_to_record(trace) if trace else None

        if db is not None:
            return await _execute(db)
        async with AsyncSessionLocal() as session:
            return await _execute(session)

    @classmethod
    def get_trace(cls, recommendation_id: str) -> Optional[RecommendationRecord]:
        """Synchronous wrapper for get_trace."""
        return _run_coroutine_sync(cls.get_trace_async(recommendation_id))

    @classmethod
    async def update_feedback_async(
        cls,
        recommendation_id: str,
        farmer_action: str,
        feedback_rating: Optional[str] = None,
        feedback_notes: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Optional[RecommendationRecord]:
        """Updates feedback on an existing trace asynchronously."""
        async def _execute(session: AsyncSession):
            repo = RecommendationRepository(session)
            trace = await repo.update_feedback(
                decision_id=recommendation_id,
                farmer_action=farmer_action,
                feedback_rating=feedback_rating,
                feedback_notes=feedback_notes,
            )
            return _trace_to_record(trace) if trace else None

        if db is not None:
            return await _execute(db)
        async with AsyncSessionLocal() as session:
            return await _execute(session)

    @classmethod
    def update_feedback(
        cls,
        recommendation_id: str,
        farmer_action: str,
        feedback_rating: Optional[str] = None,
        feedback_notes: Optional[str] = None
    ) -> Optional[RecommendationRecord]:
        """Synchronous wrapper for update_feedback."""
        return _run_coroutine_sync(
            cls.update_feedback_async(
                recommendation_id=recommendation_id,
                farmer_action=farmer_action,
                feedback_rating=feedback_rating,
                feedback_notes=feedback_notes
            )
        )

    @classmethod
    async def list_for_farmer_async(
        cls,
        farmer_id: str,
        farm_id: Optional[str] = None,
        decision_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        db: Optional[AsyncSession] = None
    ) -> List[RecommendationRecord]:
        """Lists traces for a farmer asynchronously."""
        async def _execute(session: AsyncSession):
            repo = RecommendationRepository(session)
            traces = await repo.list_for_farmer(
                farmer_id=farmer_id,
                farm_id=farm_id,
                decision_type=decision_type,
                limit=limit,
                offset=offset,
            )
            return [_trace_to_record(t) for t in traces]

        if db is not None:
            return await _execute(db)
        async with AsyncSessionLocal() as session:
            return await _execute(session)

    @classmethod
    def list_for_farmer(cls, farmer_id: str) -> List[RecommendationRecord]:
        """Synchronous wrapper for list_for_farmer."""
        return _run_coroutine_sync(cls.list_for_farmer_async(farmer_id=farmer_id))

    @classmethod
    def get_traces_for_farmer(cls, farmer_id: str) -> List[RecommendationRecord]:
        """Alias for list_for_farmer."""
        return cls.list_for_farmer(farmer_id)
