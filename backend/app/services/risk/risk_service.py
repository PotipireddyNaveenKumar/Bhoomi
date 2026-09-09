from typing import List
from app.schemas.risk import RiskAssessmentRequest, RiskAssessmentResponse, RiskDimension

class RiskAssessmentService:
    """
    Multi-dimensional Farm Risk Engine.
    Evaluates:
    1. Weather Risk
    2. Yield Risk
    3. Market Risk
    4. Crop Health Risk
    5. Economic Risk
    """
    @staticmethod
    def assess_risk(req: RiskAssessmentRequest) -> RiskAssessmentResponse:
        dimensions: List[RiskDimension] = []
        scores: List[int] = []

        # 1. Weather Risk
        weather_score = 35
        weather_factors = ["Normal diurnal temperature variation observed"]
        weather_mitigations = ["Maintain standard irrigation interval"]
        if req.rainfall_forecast_status == "high":
            weather_score = 65
            weather_factors = ["Heavy precipitation forecasted in the next 72 hours", "Risk of water stagnation and root hypoxia"]
            weather_mitigations = ["Clear field drainage channels immediately", "Pause planned irrigation cycles"]
        elif req.rainfall_forecast_status == "low" and not req.irrigation_available:
            weather_score = 80
            weather_factors = ["Rainfall deficit without protective irrigation source", "Moisture stress during sensitive stage"]
            weather_mitigations = ["Arrange tanker/contingency water supply", "Apply potassium silicate spray to reduce transpiration"]

        dimensions.append(RiskDimension(
            category="Weather Risk",
            score=weather_score,
            level="LOW" if weather_score < 40 else "MODERATE" if weather_score < 70 else "HIGH",
            factors=weather_factors,
            mitigation_actions=weather_mitigations
        ))
        scores.append(weather_score)

        # 2. Crop Health / Stage Risk
        stage_score = 30
        stage_factors = [f"Crop currently in {req.crop_stage} stage"]
        stage_mitigations = ["Follow regular scouting schedule"]
        if req.crop_stage in ["flowering", "fruit_development"]:
            stage_score = 55
            stage_factors.append("Stage is highly vulnerable to sucking pests (thrips, mites) and flower drop")
            stage_mitigations.append("Inspect 10 plants per acre twice weekly for early thrips infestation")
        
        dimensions.append(RiskDimension(
            category="Crop Health Risk",
            score=stage_score,
            level="LOW" if stage_score < 40 else "MODERATE" if stage_score < 70 else "HIGH",
            factors=stage_factors,
            mitigation_actions=stage_mitigations
        ))
        scores.append(stage_score)

        # 3. Market Risk
        market_score = 45
        market_factors = ["Moderate modal price volatility in regional mandis"]
        market_mitigations = ["Monitor weekly arrivals before scheduling harvest"]
        dimensions.append(RiskDimension(
            category="Market Risk",
            score=market_score,
            level="MODERATE",
            factors=market_factors,
            mitigation_actions=market_mitigations
        ))
        scores.append(market_score)

        # 4. Economic / Investment Risk
        econ_score = 40
        econ_factors = [f"{req.area_acres} acres cultivation investment"]
        econ_mitigations = ["Ensure input purchase receipts and quality certifications"]
        dimensions.append(RiskDimension(
            category="Economic Risk",
            score=econ_score,
            level="LOW" if econ_score < 40 else "MODERATE",
            factors=econ_factors,
            mitigation_actions=econ_mitigations
        ))
        scores.append(econ_score)

        # Overall aggregate score
        overall_score = sum(scores) // len(scores)
        overall_level = "LOW" if overall_score < 40 else "MODERATE" if overall_score < 70 else "HIGH"

        summary = (
            f"Overall farm risk is {overall_level} ({overall_score}/100) for {req.crop_name} "
            f"in {req.location} at {req.crop_stage} stage."
        )

        return RiskAssessmentResponse(
            overall_risk_score=overall_score,
            overall_risk_level=overall_level,
            summary=summary,
            dimensions=dimensions,
        )
