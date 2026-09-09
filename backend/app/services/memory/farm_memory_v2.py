from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ProvenanceType:
    SYSTEM_RECOMMENDATION = "SYSTEM_RECOMMENDATION"
    FARMER_ACTION = "FARMER_ACTION"
    FARMER_REPORTED_OUTCOME = "FARMER_REPORTED_OUTCOME"
    VERIFIED_OUTCOME = "VERIFIED_OUTCOME"


class MemoryEntry(BaseModel):
    category: str  # PREFERENCE, FARM_FACT, DECISION, CROP_HISTORY, EVENT, RECOMMENDATION, FEEDBACK, OUTCOME
    key: str
    value: Any
    confidence: float = 1.0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "farmer_dialogue"
    provenance: str = ProvenanceType.SYSTEM_RECOMMENDATION

class FarmOutcomeRecord(BaseModel):
    crop_name: str
    season: str
    year: int
    area_acres: float
    recommended_variety: str
    actual_variety_used: str
    actual_yield_quintals_per_acre: float
    total_production_quintals: float
    mandi_price_realized: float
    cultivation_cost_total: float
    net_profit_actual: float
    farmer_feedback: Optional[str] = None
    lessons_learned: Optional[str] = None
    provenance: str = ProvenanceType.FARMER_REPORTED_OUTCOME

class FarmMemoryV2:
    """
    Farm Memory 2.0 System.
    Categorizes structured episodic, procedural, and longitudinal farm memory.
    Treats past outcomes as contextual evidence, not dogma.
    Maintains strict provenance (SYSTEM_RECOMMENDATION vs FARMER_ACTION vs FARMER_REPORTED_OUTCOME vs VERIFIED_OUTCOME).
    """
    _store: Dict[str, List[MemoryEntry]] = {}
    _outcomes: Dict[str, List[FarmOutcomeRecord]] = {}

    @classmethod
    def add_memory(
        cls,
        farmer_id: str,
        category: str,
        key: str,
        value: Any,
        confidence: float = 1.0,
        source: str = "farmer_dialogue",
        provenance: str = ProvenanceType.SYSTEM_RECOMMENDATION
    ) -> MemoryEntry:
        if farmer_id not in cls._store:
            cls._store[farmer_id] = []
        entry = MemoryEntry(
            category=category,
            key=key,
            value=value,
            confidence=confidence,
            source=source,
            provenance=provenance
        )
        cls._store[farmer_id].append(entry)
        return entry

    @classmethod
    def get_memories_by_category(cls, farmer_id: str, category: str) -> List[MemoryEntry]:
        return [m for m in cls._store.get(farmer_id, []) if m.category.upper() == category.upper()]

    @classmethod
    def record_harvest_outcome(cls, farmer_id: str, outcome: FarmOutcomeRecord):
        if farmer_id not in cls._outcomes:
            cls._outcomes[farmer_id] = []
        cls._outcomes[farmer_id].append(outcome)
        # Also store as an outcome memory entry
        cls.add_memory(
            farmer_id=farmer_id,
            category="OUTCOME",
            key=f"{outcome.crop_name}_{outcome.year}_{outcome.season}",
            value=outcome.model_dump(),
            source="harvest_closure"
        )

    @classmethod
    def get_historical_outcomes(cls, farmer_id: str) -> List[FarmOutcomeRecord]:
        return cls._outcomes.get(farmer_id, [])

    @classmethod
    def get_all_context_for_farmer(cls, farmer_id: str) -> Dict[str, Any]:
        entries = cls._store.get(farmer_id, [])
        grouped = {}
        for e in entries:
            if e.category not in grouped:
                grouped[e.category] = {}
            grouped[e.category][e.key] = e.value
        return grouped

    @classmethod
    async def load_from_db(cls, db: Any, farmer_id: str):
        """Loads persisted memories from the database into the runtime store."""
        from app.repositories.memory_repo import MemoryRepository
        repo = MemoryRepository(db)
        memories = await repo.get_all_memories(farmer_id)
        for m in memories:
            cls.add_memory(
                farmer_id=farmer_id,
                category=m.category,
                key=m.key,
                value=m.value,
                confidence=m.confidence or 1.0,
                source="database"
            )

    @classmethod
    async def persist_memory(
        cls,
        db: Any,
        farmer_id: str,
        category: str,
        key: str,
        value: Any,
        confidence: float = 1.0,
        session_id: Optional[str] = None
    ) -> MemoryEntry:
        """Adds memory to runtime store and persists to database."""
        entry = cls.add_memory(farmer_id, category, key, value, confidence)
        try:
            from app.repositories.memory_repo import MemoryRepository
            repo = MemoryRepository(db)
            val_str = str(value) if not isinstance(value, str) else value
            await repo.upsert_memory(farmer_id, key, val_str, category, confidence, session_id)
        except Exception:
            pass
        return entry
