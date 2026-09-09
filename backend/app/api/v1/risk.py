from fastapi import APIRouter
from app.services.risk.risk_service import RiskAssessmentService
from app.schemas.risk import RiskAssessmentRequest, RiskAssessmentResponse

router = APIRouter(prefix="/risk", tags=["Risk Intelligence"])

@router.post("/assess", response_model=RiskAssessmentResponse)
async def assess_risk(req: RiskAssessmentRequest):
    return RiskAssessmentService.assess_risk(req)
