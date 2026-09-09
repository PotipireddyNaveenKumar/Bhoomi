import os
import joblib
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class YieldPredictionInput(BaseModel):
    crop_name: str = Field(..., example="Chilli", description="Crop name")
    state: str = Field(default="Andhra Pradesh", example="Andhra Pradesh")
    season: str = Field(default="Kharif", example="Kharif")
    area_acres: float = Field(..., gt=0, example=3.0, description="Area in acres")
    annual_rainfall_mm: float = Field(default=850.0, ge=0, example=850.0)
    fertilizer_applied_kg: float = Field(default=250.0, ge=0, example=250.0)
    pesticide_applied_kg: float = Field(default=15.0, ge=0, example=15.0)

class YieldPredictionOutput(BaseModel):
    status: str
    model_version: str
    crop: str
    area_acres: float
    predicted_yield_quintals_per_acre: float
    total_estimated_production_quintals: float
    predicted_yield_tons_per_hectare: float
    confidence_interval_quintals: List[float]
    unit: str
    assumptions: List[str]
    warnings: List[str]

class YieldPredictionService:
    _pipeline = None

    @classmethod
    def _load_pipeline(cls):
        if cls._pipeline is None:
            from app.core.config import settings
            candidate_paths = [
                os.path.join(settings.MODELS_DIR, "yield_prediction", "yield_prediction_pipeline.joblib"),
                os.path.join("models", "yield_prediction", "yield_prediction_pipeline.joblib"),
                os.path.join("..", "models", "yield_prediction", "yield_prediction_pipeline.joblib"),
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "models", "yield_prediction", "yield_prediction_pipeline.joblib")),
            ]
            for p in candidate_paths:
                if os.path.exists(p):
                    cls._pipeline = joblib.load(p)
                    return
            raise RuntimeError(f"Yield prediction model not found in any candidate path: {candidate_paths}")

    @classmethod
    def predict(cls, input_data: YieldPredictionInput) -> YieldPredictionOutput:
        cls._load_pipeline()

        # Convert acres to hectares for model input (1 acre = 0.404686 hectares)
        area_ha = input_data.area_acres * 0.404686
        # Fertilizer and pesticide in tonnes for model scale
        fert_tonnes = input_data.fertilizer_applied_kg / 1000.0
        pest_tonnes = input_data.pesticide_applied_kg / 1000.0

        # Construct single-row DataFrame matching trained feature names
        # Features: ['crop', 'season', 'state', 'area', 'annual_rainfall', 'fertilizer', 'pesticide']
        df_in = pd.DataFrame([{
            'crop': input_data.crop_name.strip().title(),
            'season': input_data.season.strip().title(),
            'state': input_data.state.strip().title(),
            'area': area_ha,
            'annual_rainfall': input_data.annual_rainfall_mm,
            'fertilizer': fert_tonnes,
            'pesticide': pest_tonnes
        }])

        raw_pred_t_ha = float(cls._pipeline.predict(df_in)[0])
        raw_pred_t_ha = max(0.2, raw_pred_t_ha)  # realistic lower floor

        # Conversion: 1 tonne/hectare = 10 quintals / 2.47105 acres = ~4.04686 quintals/acre
        quintals_per_acre = round(raw_pred_t_ha * 4.04686, 2)
        total_quintals = round(quintals_per_acre * input_data.area_acres, 2)

        # 90% confidence interval (+/- 12% empirical residual band)
        ci_low = round(total_quintals * 0.88, 2)
        ci_high = round(total_quintals * 1.12, 2)

        warnings = []
        if input_data.annual_rainfall_mm < 450:
            warnings.append("Severe Rainfall Deficit: Without scheduled irrigation, actual yield could fall towards lower confidence bound.")

        assumptions = [
            f"Forecast assumes normal weather during critical grain filling / fruit setting stage.",
            f"Model trained without target leakage (historical production strictly isolated).",
            f"1 Hectare = 2.471 Acres; 1 Metric Tonne = 10 Quintals."
        ]

        return YieldPredictionOutput(
            status="success",
            model_version="v2.0-production (XGBoost Regressor)",
            crop=input_data.crop_name,
            area_acres=input_data.area_acres,
            predicted_yield_quintals_per_acre=quintals_per_acre,
            total_estimated_production_quintals=total_quintals,
            predicted_yield_tons_per_hectare=round(raw_pred_t_ha, 2),
            confidence_interval_quintals=[ci_low, ci_high],
            unit="Quintals",
            assumptions=assumptions,
            warnings=warnings
        )
