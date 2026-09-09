from fastapi import APIRouter
from app.services.finance.profit_service import FinancialService
from app.schemas.finance import ProfitCalculationRequest, ProfitCalculationResponse

router = APIRouter(prefix="/profit", tags=["Financial Intelligence"])

@router.post("/calculate", response_model=ProfitCalculationResponse)
async def calculate_profit(req: ProfitCalculationRequest):
    return FinancialService.calculate_profit(req)
