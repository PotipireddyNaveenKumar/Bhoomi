from fastapi import APIRouter
from app.services.simulation.simulation_service import SimulationService
from app.schemas.simulation import SimulationRequest, SimulationResponse

router = APIRouter(prefix="/simulation", tags=["What-If Farm Simulator"])

@router.post("/run", response_model=SimulationResponse)
async def run_simulation(req: SimulationRequest):
    return SimulationService.run_simulation(req)
