from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.memory import FarmerMemory, MemoryCategory

class MemoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_memories(self, farmer_id: str) -> List[FarmerMemory]:
        result = await self.db.execute(
            select(FarmerMemory).where(FarmerMemory.farmer_id == farmer_id).order_by(FarmerMemory.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_memories_as_dict(self, farmer_id: str) -> Dict[str, str]:
        memories = await self.get_all_memories(farmer_id)
        return {m.key: m.value for m in memories}

    async def upsert_memory(
        self,
        farmer_id: str,
        key: str,
        value: str,
        category: str = MemoryCategory.FARM_ATTRIBUTE.value,
        confidence: float = 1.0,
        session_id: Optional[str] = None,
    ) -> FarmerMemory:
        result = await self.db.execute(
            select(FarmerMemory).where(FarmerMemory.farmer_id == farmer_id, FarmerMemory.key == key)
        )
        mem = result.scalars().first()
        if mem:
            mem.value = value
            mem.category = category
            mem.confidence = confidence
            if session_id:
                mem.source_session_id = session_id
        else:
            mem = FarmerMemory(
                farmer_id=farmer_id,
                key=key,
                value=value,
                category=category,
                confidence=confidence,
                source_session_id=session_id
            )
            self.db.add(mem)
        await self.db.commit()
        await self.db.refresh(mem)
        return mem
