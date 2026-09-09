from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.farmer_repo import FarmerRepository
from app.repositories.farm_repo import FarmRepository
from app.repositories.memory_repo import MemoryRepository

class DigitalTwinContext:
    def __init__(
        self,
        farmer_name: str,
        language: str,
        location: str,
        state: str,
        district: str,
        village: str,
        total_acres: float,
        soil_type: str,
        irrigation_source: str,
        active_crops: List[Dict[str, Any]],
        historical_crops: List[str],
        memories: Dict[str, str]
    ):
        self.farmer_name = farmer_name
        self.language = language
        self.location = location
        self.state = state
        self.district = district
        self.village = village
        self.total_acres = total_acres
        self.soil_type = soil_type
        self.irrigation_source = irrigation_source
        self.active_crops = active_crops
        self.historical_crops = historical_crops
        self.memories = memories

    def to_prompt_context(self) -> str:
        crops_str = "; ".join([
            f"{c.get('crop_name', 'Crop')} ({c.get('area_acres', self.total_acres)} acres, stage: {c.get('current_stage', 'active')}, variety: {c.get('variety', 'standard')})"
            for c in self.active_crops
        ]) if self.active_crops else "No active crops registered"

        memory_lines = "\n".join([f"  • {k}: {v}" for k, v in self.memories.items()]) or "  • None recorded yet"

        return (
            f"FARM DIGITAL TWIN CONTEXT:\n"
            f"- Farmer Name: {self.farmer_name}\n"
            f"- Preferred Language: {self.language}\n"
            f"- Location: {self.location} (State: {self.state}, District: {self.district}, Village: {self.village})\n"
            f"- Farm Land: {self.total_acres} acres | Soil Type: {self.soil_type} | Irrigation: {self.irrigation_source}\n"
            f"- Active Crops: {crops_str}\n"
            f"- Historical / Rotation Crops: {', '.join(self.historical_crops) if self.historical_crops else 'None recorded'}\n"
            f"- Long-Term Farm Memories & Preferences:\n{memory_lines}\n"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "farmer_name": self.farmer_name,
            "language": self.language,
            "location": self.location,
            "state": self.state,
            "district": self.district,
            "village": self.village,
            "total_acres": self.total_acres,
            "soil_type": self.soil_type,
            "irrigation_source": self.irrigation_source,
            "active_crops": self.active_crops,
            "historical_crops": self.historical_crops,
            "memories": self.memories
        }

class DigitalTwinService:
    """
    Assembles and maintains the complete Farmer & Farm Digital Twin.
    """
    @classmethod
    async def get_farmer_context(cls, db: AsyncSession, farmer_id: str) -> DigitalTwinContext:
        farmer_repo = FarmerRepository(db)
        farm_repo = FarmRepository(db)
        memory_repo = MemoryRepository(db)

        farmer = await farmer_repo.get_profile_by_id(farmer_id)
        if not farmer:
            return DigitalTwinContext("Farmer", "en", "India", "Andhra Pradesh", "Guntur", "", 3.0, "black", "borewell", [], [], {})

        farms = await farm_repo.get_farms_by_farmer(farmer_id)
        active_crops = []
        total_acres = 0.0
        soil_type = "black"
        irr_source = "borewell"

        for farm in farms:
            total_acres += float(farm.total_area_acres)
            if farm.soil_type:
                soil_type = farm.soil_type
            if farm.irrigation_source:
                irr_source = farm.irrigation_source

            for c in farm.crops:
                active_crops.append({
                    "crop_id": c.id,
                    "crop_name": c.crop_name,
                    "variety": c.variety or "Teja",
                    "area_acres": float(c.area_acres),
                    "current_stage": c.current_stage,
                    "status": c.status,
                    "sowing_date": str(c.sowing_date) if c.sowing_date else None,
                    "expected_harvest": str(c.expected_harvest_date) if c.expected_harvest_date else None
                })

        memories = await memory_repo.get_memories_as_dict(farmer_id)
        location = f"{farmer.village or ''}, {farmer.district or 'Guntur'}, {farmer.state or 'Andhra Pradesh'}".strip(", ")

        historical = [v for k, v in memories.items() if "history" in k or "previous_crop" in k]

        return DigitalTwinContext(
            farmer_name=farmer.name,
            language=farmer.preferred_language,
            location=location,
            state=farmer.state or "Andhra Pradesh",
            district=farmer.district or "Guntur",
            village=farmer.village or "Tenali",
            total_acres=round(total_acres, 1) if total_acres > 0 else 3.0,
            soil_type=soil_type,
            irrigation_source=irr_source,
            active_crops=active_crops,
            historical_crops=historical,
            memories=memories
        )
