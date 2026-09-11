from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.farmer_repo import FarmerRepository
from app.repositories.farm_repo import FarmRepository
from app.repositories.memory_repo import MemoryRepository

class DigitalTwinContext:
    def __init__(
        self,
        farmer_name: str = "Farmer",
        language: str = "en",
        location: str = "Farm",
        state: str = "",
        district: str = "",
        village: str = "",
        total_acres: float = 1.0,
        soil_type: str = "Loam",
        irrigation_source: str = "Rainfed",
        active_crops: Optional[List[Dict[str, Any]]] = None,
        historical_crops: Optional[List[str]] = None,
        memories: Optional[Dict[str, str]] = None,
        farm_id: Optional[str] = None,
        soil_health_data: Optional[Dict[str, Any]] = None,
        farmer_id: Optional[str] = None,
        total_land_acres: Optional[float] = None,
        soil_ph: Optional[float] = None,
        soil_n: Optional[float] = None,
        soil_p: Optional[float] = None,
        soil_k: Optional[float] = None,
        **kwargs
    ):
        self.farmer_name = farmer_name
        self.farmer_id = farmer_id
        self.language = language
        self.location = location
        self.state = state
        self.district = district
        self.village = village
        self.total_acres = total_acres if total_land_acres is None else total_land_acres
        self.soil_type = soil_type
        self.irrigation_source = irrigation_source
        self.active_crops = active_crops or []
        self.historical_crops = historical_crops or []
        self.memories = memories or {}
        self.farm_id = farm_id
        self.soil_health_data = soil_health_data or {}
        
        # Helper properties for soil nutrients
        self.soil_ph = soil_ph
        self.soil_n = soil_n
        self.soil_p = soil_p
        self.soil_k = soil_k
        if self.soil_health_data:
            ph_entry = self.soil_health_data.get("pH")
            if ph_entry is not None:
                self.soil_ph = ph_entry.get("value") if isinstance(ph_entry, dict) else ph_entry
            n_entry = self.soil_health_data.get("nitrogen")
            if n_entry is not None:
                self.soil_n = n_entry.get("value") if isinstance(n_entry, dict) else n_entry
            p_entry = self.soil_health_data.get("phosphorus")
            if p_entry is not None:
                self.soil_p = p_entry.get("value") if isinstance(p_entry, dict) else p_entry
            k_entry = self.soil_health_data.get("potassium")
            if k_entry is not None:
                self.soil_k = k_entry.get("value") if isinstance(k_entry, dict) else k_entry

    def to_prompt_context(self) -> str:
        crops_str = "; ".join([
            f"{c.get('crop_name', 'Crop')} ({c.get('area_acres', self.total_acres)} acres, stage: {c.get('current_stage', 'active')}, variety: {c.get('variety', 'Standard')})"
            for c in self.active_crops
        ]) if self.active_crops else "No active crops registered"

        memory_lines = "\n".join([f"  • {k}: {v}" for k, v in self.memories.items()]) or "  • None recorded yet"

        soil_provenance_str = ""
        if self.soil_health_data:
            ph_val = self.soil_ph or "Not specified"
            soil_provenance_str = f" | Estimated pH: {ph_val}"

        return (
            f"FARM DIGITAL TWIN CONTEXT:\n"
            f"- Farmer Name: {self.farmer_name}\n"
            f"- Preferred Language: {self.language}\n"
            f"- Location: {self.location} (State: {self.state}, District: {self.district}, Village: {self.village})\n"
            f"- Farm Land: {self.total_acres} acres | Soil Type: {self.soil_type}{soil_provenance_str} | Irrigation: {self.irrigation_source}\n"
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
            "memories": self.memories,
            "farm_id": self.farm_id,
            "soil_health_data": self.soil_health_data
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
            return DigitalTwinContext("Farmer", "en", "India", "Telangana", "Warangal", "", 3.0, "red", "borewell", [], [], {})

        farms = await farm_repo.get_farms_by_farmer(farmer_id)
        active_crops = []
        total_acres = 0.0
        soil_type = "red" if (farmer.state == "Telangana") else "black"
        irr_source = "borewell"
        farm_id = None
        soil_health_data = {}

        for farm in farms:
            if not farm_id:
                farm_id = farm.id
            total_acres += float(farm.total_area_acres)
            if farm.soil_type:
                soil_type = farm.soil_type
            if farm.irrigation_source:
                irr_source = farm.irrigation_source
            if farm.soil_health_data:
                soil_health_data = farm.soil_health_data

            for c in farm.crops:
                active_crops.append({
                    "crop_id": c.id,
                    "crop_name": c.crop_name,
                    "variety": c.variety or "Standard",
                    "area_acres": float(c.area_acres),
                    "current_stage": c.current_stage,
                    "status": c.status,
                    "sowing_date": str(c.sowing_date) if c.sowing_date else None,
                    "expected_harvest": str(c.expected_harvest_date) if c.expected_harvest_date else None
                })

        memories = await memory_repo.get_memories_as_dict(farmer_id)
        location = f"{farmer.village or ''}, {farmer.district or 'Warangal'}, {farmer.state or 'Telangana'}".strip(", ")

        historical = [v for k, v in memories.items() if "history" in k or "previous_crop" in k]

        return DigitalTwinContext(
            farmer_name=farmer.name,
            language=farmer.preferred_language,
            location=location,
            state=farmer.state or "Telangana",
            district=farmer.district or "Warangal",
            village=farmer.village or "Rural",
            total_acres=round(total_acres, 1) if total_acres > 0 else 3.0,
            soil_type=soil_type,
            irrigation_source=irr_source,
            active_crops=active_crops,
            historical_crops=historical,
            memories=memories,
            farm_id=farm_id,
            soil_health_data=soil_health_data
        )
