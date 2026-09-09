import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.services.farm_manager.state_engine import FarmState


class AggregatedRisk(BaseModel):
    risk_id: str = Field(default_factory=lambda: f"risk_{uuid.uuid4().hex[:8]}")
    category: str  # WEATHER, WATER, CROP_HEALTH, MARKET, YIELD, FINANCIAL, TASK, DATA_QUALITY
    severity: str  # CRITICAL, HIGH, MODERATE, LOW
    probability: Optional[float] = None  # Numerical only if rule/model grounded; else None
    qualitative_probability: str = "ESTIMATED"  # HIGH, MODERATE, LOW, UNKNOWN
    impact: str
    confidence: float = 0.85
    evidence: str
    recommended_mitigation: str


class FarmRiskAggregator:
    """
    Farm Risk Aggregator.
    Aggregates multi-dimensional operational risks across 8 canonical categories:
    WEATHER, WATER, CROP_HEALTH, MARKET, YIELD, FINANCIAL, TASK, DATA_QUALITY.
    Enforces qualitative severity whenever mathematical probabilities are ungrounded.
    """

    @classmethod
    def evaluate_risks(cls, state: FarmState) -> List[AggregatedRisk]:
        risks: List[AggregatedRisk] = []

        rain_prob = state.weather_summary.get("rain_probability", 0)
        rainfall_mm = state.weather_summary.get("rainfall_mm", 0.0)

        # 1. WEATHER Risk
        if rain_prob >= 70 or rainfall_mm >= 25.0:
            risks.append(AggregatedRisk(
                category="WEATHER",
                severity="HIGH",
                probability=float(rain_prob) / 100.0,
                qualitative_probability="HIGH",
                impact="Heavy unseasonal rainfall may cause surface waterlogging and flower drop.",
                confidence=0.90,
                evidence=f"IMD Weather Advisory: {rain_prob}% rain probability, {rainfall_mm}mm precipitation.",
                recommended_mitigation="Inspect and clear field perimeter drainage channels immediately."
            ))
        elif rain_prob <= 10 and state.weather_summary.get("temperature", 30.0) >= 38.0:
            risks.append(AggregatedRisk(
                category="WEATHER",
                severity="MODERATE",
                probability=None,
                qualitative_probability="MODERATE",
                impact="Heat stress may cause blossom-end rot and rapid soil drying.",
                confidence=0.85,
                evidence="High ambient temperature (>38°C) with dry atmospheric conditions.",
                recommended_mitigation="Apply light micro-sprinkler or furrow irrigation during early morning hours."
            ))

        # 2. WATER Risk
        if state.soil_moisture_percentage and state.soil_moisture_percentage < 30.0:
            risks.append(AggregatedRisk(
                category="WATER",
                severity="HIGH" if state.crop_stage.lower() in ["flowering", "fruit_development"] else "MODERATE",
                probability=None,
                qualitative_probability="HIGH",
                impact="Root zone moisture deficit during critical stage will reduce yield.",
                confidence=0.88,
                evidence=f"Measured/estimated soil moisture is {state.soil_moisture_percentage}%, below critical 35% baseline.",
                recommended_mitigation="Schedule immediate irrigation before moisture tension causes permanent wilting."
            ))

        # 3. CROP_HEALTH Risk
        if state.recent_disease_detection:
            risks.append(AggregatedRisk(
                category="CROP_HEALTH",
                severity="CRITICAL" if "blight" in state.recent_disease_detection.lower() or "virus" in state.recent_disease_detection.lower() else "HIGH",
                probability=None,
                qualitative_probability="CONFIRMED",
                impact=f"Active {state.recent_disease_detection} infection threatens canopy loss.",
                confidence=0.92,
                evidence=f"Field diagnosis confirmed: {state.recent_disease_detection}.",
                recommended_mitigation="Apply approved CIBRC fungicide/bactericide or bio-control agent; remove infected plant debris."
            ))

        # 4. MARKET Risk
        if state.market_modal_price_per_quintal < 10000.0:
            risks.append(AggregatedRisk(
                category="MARKET",
                severity="MODERATE",
                probability=None,
                qualitative_probability="OBSERVED",
                impact="Mandi spot price softened below standard commercial target.",
                confidence=0.85,
                evidence=f"Current modal price ₹{state.market_modal_price_per_quintal:,.0f}/Q at {state.best_mandi_name}.",
                recommended_mitigation="Hold stock in licensed cold storage or delay harvest picking if possible."
            ))

        # 5. YIELD Risk
        if state.crop_stage.lower() == "flowering" and rain_prob >= 50:
            risks.append(AggregatedRisk(
                category="YIELD",
                severity="HIGH",
                probability=None,
                qualitative_probability="HIGH",
                impact="Rain during peak anthesis (flowering) disrupts pollination and causes flower drop.",
                confidence=0.87,
                evidence="Crop in peak flowering concurrent with forecasted precipitation.",
                recommended_mitigation="Apply 19:19:19 + Boron foliar spray post-rain to restore pollen viability."
            ))

        # 6. FINANCIAL Risk
        if state.net_realization_per_quintal is None:
            risks.append(AggregatedRisk(
                category="FINANCIAL",
                severity="MODERATE",
                probability=None,
                qualitative_probability="HIGH",
                impact="Incomplete transport/mandi fee data prevents accurate profit calculation.",
                confidence=0.80,
                evidence="Transport cost or APMC cess is unverified for remote mandi.",
                recommended_mitigation="Verify freight rate with local trucker association before dispatch."
            ))

        # 7. TASK Risk
        risks.append(AggregatedRisk(
            category="TASK",
            severity="LOW",
            probability=None,
            qualitative_probability="ROUTINE",
            impact="Routine intercultural weeding and trellising maintenance.",
            confidence=0.90,
            evidence="Standard stage-wise crop calendar.",
            recommended_mitigation="Maintain scheduled farm labor for intercultural operations."
        ))

        # 8. DATA_QUALITY Risk
        freshness = state.data_freshness
        stale_sources = [k for k, v in freshness.items() if getattr(v, "freshness_status", "") in ["STALE", "UNAVAILABLE"]]
        if stale_sources:
            risks.append(AggregatedRisk(
                category="DATA_QUALITY",
                severity="MODERATE",
                probability=None,
                qualitative_probability="OBSERVED",
                impact=f"Stale or unavailable telemetry for {', '.join(stale_sources)} increases decision uncertainty.",
                confidence=0.95,
                evidence=f"Data freshness status flagged as non-current for: {', '.join(stale_sources)}.",
                recommended_mitigation="Verify ground observations manually before executing major chemical or harvest actions."
            ))

        # Sort by severity: CRITICAL -> HIGH -> MODERATE -> LOW
        sev_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
        risks.sort(key=lambda r: sev_order.get(r.severity, 4))
        return risks
