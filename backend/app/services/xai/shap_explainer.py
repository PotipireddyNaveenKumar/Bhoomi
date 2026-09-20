import os
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
import joblib

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    shap = None
    SHAP_AVAILABLE = False

from app.services.xai.explanation_model import (
    FeatureContribution,
    ModelExplanation,
    XAICapabilityStatus
)
from app.services.crop.recommendation_service import (
    CropRecommendationService,
    CropRecommendationInput,
    CropRecommendationOutput
)
from app.services.yield_prediction.yield_service import (
    YieldPredictionService,
    YieldPredictionInput,
    YieldPredictionOutput
)
from app.services.crop.fertilizer_service import (
    FertilizerRecommendationService,
    FertilizerInput,
    FertilizerRecommendationOutput
)

logger = logging.getLogger(__name__)


class TabularSHAPExplainer:
    """
    Production SHAP Attribution Engine for BHOOMI Tabular Models.
    Computes exact TreeSHAP attributions using the authentic models and inputs.
    Strictly forbids fake SHAP values or random attributions.
    """

    _crop_explainer = None
    _yield_explainer = None
    _fert_explainer = None
    _fert_pipeline = None
    _fert_encoder = None

    # -------------------------------------------------------------
    # 1. CROP RECOMMENDATION SHAP
    # -------------------------------------------------------------
    @classmethod
    def _get_crop_explainer(cls):
        if cls._crop_explainer is None and SHAP_AVAILABLE:
            CropRecommendationService._load_artifacts()
            if CropRecommendationService._model is not None:
                cls._crop_explainer = shap.TreeExplainer(CropRecommendationService._model)
        return cls._crop_explainer

    @classmethod
    def explain_crop_recommendation(
        cls,
        input_data: CropRecommendationInput,
        prediction_output: Optional[CropRecommendationOutput] = None,
        top_k_factors: int = 3
    ) -> ModelExplanation:
        """
        Computes exact TreeSHAP values for CropRecommendationService (RandomForestClassifier).
        """
        if not prediction_output:
            prediction_output = CropRecommendationService.predict(input_data)

        if not SHAP_AVAILABLE:
            return ModelExplanation(
                model_name="RandomForestClassifier",
                model_version=prediction_output.model_version,
                prediction=prediction_output.recommended_crops[0].crop if prediction_output.recommended_crops else "Unknown",
                input_features_used=prediction_output.input_summary,
                explanation_summary="SHAP library unavailable in runtime.",
                xai_status=XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value,
                confidence=prediction_output.recommended_crops[0].confidence if prediction_output.recommended_crops else None
            )

        try:
            explainer = cls._get_crop_explainer()
            if explainer is None:
                raise RuntimeError("Crop model TreeExplainer could not be initialized.")

            raw_features = [
                input_data.nitrogen,
                input_data.phosphorus,
                input_data.potassium,
                input_data.temperature,
                input_data.humidity,
                input_data.ph,
                input_data.rainfall
            ]
            feature_names = ["nitrogen", "phosphorus", "potassium", "temperature", "humidity", "ph", "rainfall"]
            input_features_dict = dict(zip(feature_names, raw_features))

            features_array = np.array([raw_features])
            features_scaled = CropRecommendationService._scaler.transform(features_array)

            # Compute exact SHAP values
            shap_raw = explainer.shap_values(features_scaled)

            # Target predicted class index
            primary_crop = prediction_output.recommended_crops[0].crop
            class_classes = [c.lower() for c in CropRecommendationService._label_encoder.classes_]
            target_idx = class_classes.index(primary_crop.lower()) if primary_crop.lower() in class_classes else 0

            # Handle shap_values output shape: (1, n_features, n_classes) or list of (1, n_features)
            if isinstance(shap_raw, list):
                class_shap = shap_raw[target_idx][0]
            elif len(shap_raw.shape) == 3:
                class_shap = shap_raw[0, :, target_idx]
            else:
                class_shap = shap_raw[0]

            contributions: List[FeatureContribution] = []
            for name, val, sv in zip(feature_names, raw_features, class_shap):
                s_float = float(round(sv, 4))
                direction = "positive" if s_float > 0 else "negative" if s_float < 0 else "neutral"
                contributions.append(FeatureContribution(
                    feature=name,
                    value=val,
                    shap_value=s_float,
                    impact_direction=direction,
                    display_name=name.title(),
                    display_text=f"{name.title()} ({val}) {'contributed favorably' if s_float > 0 else 'reduced suitability'} by {abs(s_float):.2f}"
                ))

            # Partition into top positive and top negative
            pos_factors = sorted([c for c in contributions if c.shap_value > 0], key=lambda x: x.shap_value, reverse=True)[:top_k_factors]
            neg_factors = sorted([c for c in contributions if c.shap_value < 0], key=lambda x: x.shap_value)[:top_k_factors]

            pos_names = ", ".join([f"{f.feature} ({f.value})" for f in pos_factors]) or "general balance"
            summary = (
                f"RandomForest model selected {primary_crop} primarily supported by {pos_names}."
            )

            base_val = None
            if hasattr(explainer, "expected_value"):
                ev = explainer.expected_value
                base_val = float(ev[target_idx]) if isinstance(ev, (list, np.ndarray)) else float(ev)

            legitimate_conf = float(prediction_output.recommended_crops[0].confidence)

            return ModelExplanation(
                model_name=prediction_output.model_name,
                model_version=prediction_output.model_version,
                prediction=primary_crop,
                input_features_used=input_features_dict,
                top_positive_factors=pos_factors,
                top_negative_factors=neg_factors,
                all_contributions=contributions,
                base_value=base_val,
                confidence=legitimate_conf,
                explanation_summary=summary,
                xai_status=XAICapabilityStatus.AVAILABLE.value
            )
        except Exception as e:
            logger.error(f"[SHAP_CROP] Crop SHAP attribution failed: {e}")
            return ModelExplanation(
                model_name="RandomForestClassifier",
                model_version=getattr(prediction_output, "model_version", "v2.0-production"),
                prediction=prediction_output.recommended_crops[0].crop if (prediction_output and prediction_output.recommended_crops) else "Unknown",
                input_features_used=getattr(prediction_output, "input_summary", {}),
                explanation_summary=f"SHAP attribution computation failed: {str(e)}",
                xai_status=XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value,
                confidence=prediction_output.recommended_crops[0].confidence if (prediction_output and prediction_output.recommended_crops) else None
            )

    # -------------------------------------------------------------
    # 2. YIELD PREDICTION SHAP
    # -------------------------------------------------------------
    @classmethod
    def _get_yield_explainer(cls):
        if cls._yield_explainer is None and SHAP_AVAILABLE:
            YieldPredictionService._load_pipeline()
            if YieldPredictionService._pipeline is not None:
                regressor = YieldPredictionService._pipeline.named_steps["regressor"]
                cls._yield_explainer = shap.TreeExplainer(regressor)
        return cls._yield_explainer

    @classmethod
    def explain_yield_prediction(
        cls,
        input_data: YieldPredictionInput,
        prediction_output: Optional[YieldPredictionOutput] = None,
        top_k_factors: int = 3
    ) -> ModelExplanation:
        """
        Computes exact TreeSHAP values for YieldPredictionService (XGBoost Regressor Pipeline).
        """
        if not prediction_output:
            prediction_output = YieldPredictionService.predict(input_data)

        if not SHAP_AVAILABLE:
            return ModelExplanation(
                model_name="XGBoost Regressor",
                model_version=prediction_output.model_version,
                prediction=prediction_output.predicted_yield_quintals_per_acre,
                input_features_used=input_data.model_dump(),
                explanation_summary="SHAP library unavailable in runtime.",
                xai_status=XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value,
                confidence=None
            )

        try:
            YieldPredictionService._load_pipeline()
            pipeline = YieldPredictionService._pipeline
            preprocessor = pipeline.named_steps["preprocessor"]
            explainer = cls._get_yield_explainer()

            area_ha = input_data.area_acres * 0.404686
            fert_tonnes = input_data.fertilizer_applied_kg / 1000.0
            pest_tonnes = input_data.pesticide_applied_kg / 1000.0

            df_in = pd.DataFrame([{
                'crop': input_data.crop_name.strip().title(),
                'season': input_data.season.strip().title(),
                'state': input_data.state.strip().title(),
                'area': area_ha,
                'annual_rainfall': input_data.annual_rainfall_mm,
                'fertilizer': fert_tonnes,
                'pesticide': pest_tonnes
            }])

            transformed = preprocessor.transform(df_in)
            transformed_feature_names = preprocessor.get_feature_names_out()

            # Compute exact TreeSHAP
            shap_raw = explainer.shap_values(transformed)
            shap_arr = shap_raw[0] if len(shap_raw.shape) > 1 else shap_raw

            # Aggregate one-hot categorical SHAP values back to their original domain features
            # Original features: area, annual_rainfall, fertilizer, pesticide, crop, season, state
            feature_shap_map: Dict[str, float] = {
                "crop": 0.0,
                "season": 0.0,
                "state": 0.0,
                "area": 0.0,
                "annual_rainfall": 0.0,
                "fertilizer": 0.0,
                "pesticide": 0.0
            }

            for f_name, sv in zip(transformed_feature_names, shap_arr):
                s_float = float(sv)
                if "cat__crop_" in f_name:
                    feature_shap_map["crop"] += s_float
                elif "cat__season_" in f_name:
                    feature_shap_map["season"] += s_float
                elif "cat__state_" in f_name:
                    feature_shap_map["state"] += s_float
                elif "num__area" in f_name:
                    feature_shap_map["area"] += s_float
                elif "num__annual_rainfall" in f_name:
                    feature_shap_map["annual_rainfall"] += s_float
                elif "num__fertilizer" in f_name:
                    feature_shap_map["fertilizer"] += s_float
                elif "num__pesticide" in f_name:
                    feature_shap_map["pesticide"] += s_float

            user_values = {
                "crop": input_data.crop_name,
                "season": input_data.season,
                "state": input_data.state,
                "area": f"{input_data.area_acres} acres",
                "annual_rainfall": f"{input_data.annual_rainfall_mm} mm",
                "fertilizer": f"{input_data.fertilizer_applied_kg} kg",
                "pesticide": f"{input_data.pesticide_applied_kg} kg"
            }

            CONVERSION_T_HA_TO_Q_ACRE = 4.04686
            contributions: List[FeatureContribution] = []
            for f_key, sv in feature_shap_map.items():
                s_float = float(round(sv, 4))
                s_conv = float(round(s_float * CONVERSION_T_HA_TO_Q_ACRE, 4))
                direction = "positive" if s_float > 0 else "negative" if s_float < 0 else "neutral"
                contributions.append(FeatureContribution(
                    feature=f_key,
                    value=user_values[f_key],
                    shap_value=s_float,
                    impact_direction=direction,
                    display_name=f_key.replace("_", " ").title(),
                    display_text=f"{f_key.replace('_', ' ').title()} ({user_values[f_key]}) {'increased' if s_float > 0 else 'decreased'} forecast by {abs(s_float):.2f} t/ha ({abs(s_conv):.2f} quintals/acre)"
                ))

            pos_factors = sorted([c for c in contributions if c.shap_value > 0], key=lambda x: x.shap_value, reverse=True)[:top_k_factors]
            neg_factors = sorted([c for c in contributions if c.shap_value < 0], key=lambda x: x.shap_value)[:top_k_factors]

            pos_names = ", ".join([f"{f.feature} ({f.value})" for f in pos_factors]) or "baseline trends"
            native_pred_t_ha = float(getattr(prediction_output, "predicted_yield_tons_per_hectare", 0.0))
            disp_pred_q_acre = float(getattr(prediction_output, "predicted_yield_quintals_per_acre", round(native_pred_t_ha * CONVERSION_T_HA_TO_Q_ACRE, 2)))

            summary = (
                f"XGBoost yield forecast of {native_pred_t_ha:.2f} t/ha ({disp_pred_q_acre:.2f} quintals/acre) "
                f"was positively influenced by {pos_names}. (Native model space: tonnes/hectare; Display conversion: 1 t/ha = {CONVERSION_T_HA_TO_Q_ACRE} quintals/acre)."
            )

            base_val = float(round(explainer.expected_value, 4)) if hasattr(explainer, "expected_value") else None

            # Do NOT invent a fake confidence score. The model output provides an empirical 90% confidence interval.
            return ModelExplanation(
                model_name="XGBoost Regressor",
                model_version=prediction_output.model_version,
                prediction=f"{disp_pred_q_acre} quintals/acre ({native_pred_t_ha} t/ha)",
                input_features_used=user_values,
                top_positive_factors=pos_factors,
                top_negative_factors=neg_factors,
                all_contributions=contributions,
                base_value=base_val,
                confidence=None,  # Not fabricated; empirical confidence interval in prediction_output
                explanation_summary=summary,
                xai_status=XAICapabilityStatus.AVAILABLE.value,
                native_unit="tonnes/hectare",
                display_unit="quintals/acre",
                conversion_factor=CONVERSION_T_HA_TO_Q_ACRE
            )
        except Exception as e:
            logger.error(f"[SHAP_YIELD] Yield SHAP attribution failed: {e}")
            return ModelExplanation(
                model_name="XGBoost Regressor",
                model_version=getattr(prediction_output, "model_version", "v2.0-production"),
                prediction=getattr(prediction_output, "predicted_yield_quintals_per_acre", 0.0),
                input_features_used=input_data.model_dump(),
                explanation_summary=f"Yield SHAP computation failed: {str(e)}",
                xai_status=XAICapabilityStatus.UNAVAILABLE_FOR_CURRENT_MODEL.value,
                confidence=None
            )

    # -------------------------------------------------------------
    # 3. FERTILIZER RECOMMENDATION SHAP / HEURISTIC EXPLANATION
    # -------------------------------------------------------------
    @classmethod
    def _load_fertilizer_pipeline(cls):
        if cls._fert_pipeline is None:
            from app.core.config import settings
            candidates = [
                os.path.join(settings.MODELS_DIR, "fertilizer_recommendation", "fertilizer_pipeline.joblib"),
                "models/fertilizer_recommendation/fertilizer_pipeline.joblib",
                "../models/fertilizer_recommendation/fertilizer_pipeline.joblib",
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "models", "fertilizer_recommendation", "fertilizer_pipeline.joblib")),
            ]
            for p in candidates:
                if os.path.exists(p):
                    try:
                        cls._fert_pipeline = joblib.load(p)
                        enc_p = os.path.join(os.path.dirname(p), "fertilizer_label_encoder.joblib")
                        if os.path.exists(enc_p):
                            cls._fert_encoder = joblib.load(enc_p)
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load fertilizer pipeline: {e}")

    @classmethod
    def explain_fertilizer_recommendation(
        cls,
        input_data: FertilizerInput,
        prediction_output: Optional[FertilizerRecommendationOutput] = None,
        top_k_factors: int = 3
    ) -> ModelExplanation:
        """
        Produces genuine explanation for fertilizer recommendation.
        If fertilizer_pipeline.joblib is present and SHAP is available, computes exact TreeSHAP.
        Otherwise provides structured agronomic heuristic attribution without fabricating SHAP values.
        """
        if not prediction_output:
            prediction_output = FertilizerRecommendationService.recommend(input_data)

        cls._load_fertilizer_pipeline()

        # If trained pipeline is available and SHAP is active:
        if cls._fert_pipeline is not None and SHAP_AVAILABLE:
            try:
                preprocessor = cls._fert_pipeline.named_steps["preprocessor"]
                classifier = cls._fert_pipeline.named_steps["classifier"]
                if cls._fert_explainer is None:
                    cls._fert_explainer = shap.TreeExplainer(classifier)

                # Map input features to pipeline schema
                # ['temperature', 'humidity', 'moisture', 'nitrogen', 'potassium', 'phosphorus', 'soil_type', 'crop_type']
                df_fert = pd.DataFrame([{
                    "temperature": input_data.temperature,
                    "humidity": input_data.humidity,
                    "moisture": input_data.moisture,
                    "nitrogen": input_data.nitrogen,
                    "potassium": input_data.potassium,
                    "phosphorus": input_data.phosphorus,
                    "soil_type": input_data.soil_type.strip().title(),
                    "crop_type": input_data.crop_name.strip().title()
                }])

                transformed = preprocessor.transform(df_fert)
                shap_raw = cls._fert_explainer.shap_values(transformed)

                # Get predicted class from pipeline
                pred_class_idx = int(classifier.predict(transformed)[0])
                pred_label = cls._fert_encoder.classes_[pred_class_idx] if cls._fert_encoder else str(pred_class_idx)

                # Extract SHAP for this class
                if isinstance(shap_raw, list):
                    class_shap = shap_raw[pred_class_idx][0]
                elif len(shap_raw.shape) == 3:
                    class_shap = shap_raw[0, :, pred_class_idx]
                else:
                    class_shap = shap_raw[0]

                t_names = preprocessor.get_feature_names_out()
                feature_map: Dict[str, float] = {
                    "nitrogen": 0.0,
                    "phosphorus": 0.0,
                    "potassium": 0.0,
                    "moisture": 0.0,
                    "temperature": 0.0,
                    "humidity": 0.0,
                    "soil_type": 0.0,
                    "crop_type": 0.0
                }

                for name, sv in zip(t_names, class_shap):
                    sv_f = float(sv)
                    if "nitrogen" in name:
                        feature_map["nitrogen"] += sv_f
                    elif "phosphorus" in name:
                        feature_map["phosphorus"] += sv_f
                    elif "potassium" in name:
                        feature_map["potassium"] += sv_f
                    elif "moisture" in name:
                        feature_map["moisture"] += sv_f
                    elif "temperature" in name:
                        feature_map["temperature"] += sv_f
                    elif "humidity" in name:
                        feature_map["humidity"] += sv_f
                    elif "soil_type" in name:
                        feature_map["soil_type"] += sv_f
                    elif "crop_type" in name:
                        feature_map["crop_type"] += sv_f

                user_vals = {
                    "nitrogen": input_data.nitrogen,
                    "phosphorus": input_data.phosphorus,
                    "potassium": input_data.potassium,
                    "moisture": input_data.moisture,
                    "temperature": input_data.temperature,
                    "humidity": input_data.humidity,
                    "soil_type": input_data.soil_type,
                    "crop_type": input_data.crop_name
                }

                contributions: List[FeatureContribution] = []
                for k, sv in feature_map.items():
                    sv_round = float(round(sv, 4))
                    direction = "positive" if sv_round > 0 else "negative" if sv_round < 0 else "neutral"
                    contributions.append(FeatureContribution(
                        feature=k,
                        value=user_vals[k],
                        shap_value=sv_round,
                        impact_direction=direction,
                        display_name=k.replace("_", " ").title(),
                        display_text=f"{k.replace('_', ' ').title()} ({user_vals[k]}) {'favored' if sv_round > 0 else 'discouraged'} {pred_label}"
                    ))

                pos_factors = sorted([c for c in contributions if c.shap_value > 0], key=lambda x: x.shap_value, reverse=True)[:top_k_factors]
                neg_factors = sorted([c for c in contributions if c.shap_value < 0], key=lambda x: x.shap_value)[:top_k_factors]

                summary = f"Fertilizer model selected {pred_label} with primary driver: {pos_factors[0].feature} ({pos_factors[0].value})" if pos_factors else f"Selected {pred_label}"

                return ModelExplanation(
                    model_name="RandomForestClassifier (Fertilizer Pipeline)",
                    model_version="v1.0-production",
                    prediction=prediction_output.recommended_fertilizer,
                    input_features_used=user_vals,
                    top_positive_factors=pos_factors,
                    top_negative_factors=neg_factors,
                    all_contributions=contributions,
                    base_value=None,
                    confidence=None,
                    explanation_summary=summary,
                    xai_status=XAICapabilityStatus.AVAILABLE.value
                )
            except Exception as e:
                logger.warning(f"Fertilizer pipeline SHAP calculation failed: {e}")

        # Agronomic Rule / ICAR Knowledge Base attribution
        # Expose legitimate feature values and actual deficit drivers without claiming fake SHAP
        nutrient_factors: List[FeatureContribution] = []
        if input_data.nitrogen < 50:
            nutrient_factors.append(FeatureContribution(
                feature="nitrogen",
                value=input_data.nitrogen,
                shap_value=0.0,
                impact_direction="positive",
                display_name="Soil Available Nitrogen",
                display_text=f"Soil nitrogen is low ({input_data.nitrogen} kg/ha index), requiring nitrogen supplementation."
            ))
        if input_data.phosphorus < 25:
            nutrient_factors.append(FeatureContribution(
                feature="phosphorus",
                value=input_data.phosphorus,
                shap_value=0.0,
                impact_direction="positive",
                display_name="Soil Available Phosphorus",
                display_text=f"Soil phosphorus is low ({input_data.phosphorus} kg/ha index), requiring phosphate application."
            ))
        if input_data.potassium < 40:
            nutrient_factors.append(FeatureContribution(
                feature="potassium",
                value=input_data.potassium,
                shap_value=0.0,
                impact_direction="positive",
                display_name="Soil Available Potassium",
                display_text=f"Soil potassium is low ({input_data.potassium} kg/ha index), requiring potash amendment."
            ))

        return ModelExplanation(
            model_name="ICAR / SAU Agronomic Knowledge Base",
            model_version="v2.0-agronomic",
            prediction=prediction_output.recommended_fertilizer,
            input_features_used=input_data.model_dump(),
            top_positive_factors=nutrient_factors,
            top_negative_factors=[],
            all_contributions=nutrient_factors,
            base_value=None,
            confidence=0.95 if "ICAR" in prediction_output.confidence_level else 0.75,
            explanation_summary=(
                f"Recommendation '{prediction_output.recommended_fertilizer}' derived from {prediction_output.evidence_source} "
                f"addressing {prediction_output.nutrient_deficiency} at {prediction_output.crop_stage} stage."
            ),
            xai_status=XAICapabilityStatus.HEURISTIC_ATTRIBUTION.value
        )

    # -------------------------------------------------------------
    # 4. RISK PREDICTION AUDIT
    # -------------------------------------------------------------
    @classmethod
    def explain_risk_model(cls, risk_request: Any, risk_response: Any) -> ModelExplanation:
        """
        Risk assessment is calculated from deterministic multi-dimensional domain heuristics,
        not a trained tabular ML model with weight gradients.
        Explicitly documents capability status per Task 1 / Task 5 requirements.
        """
        features = risk_request.model_dump() if hasattr(risk_request, "model_dump") else dict(risk_request)
        dim_factors: List[FeatureContribution] = []
        if hasattr(risk_response, "dimensions"):
            for d in risk_response.dimensions:
                dim_factors.append(FeatureContribution(
                    feature=d.category.lower().replace(" ", "_"),
                    value=f"{d.score}/100 ({d.level})",
                    shap_value=float(d.score),
                    impact_direction="negative" if d.score >= 70 else "neutral" if d.score >= 40 else "positive",
                    display_name=d.category,
                    display_text=f"{d.category}: {', '.join(d.factors[:1])}"
                ))

        return ModelExplanation(
            model_name="FarmRiskEngine (Heuristic)",
            model_version="v2.0-deterministic",
            prediction=getattr(risk_response, "overall_risk_level", "MODERATE"),
            input_features_used=features,
            top_positive_factors=[f for f in dim_factors if f.impact_direction == "positive"],
            top_negative_factors=[f for f in dim_factors if f.impact_direction == "negative"],
            all_contributions=dim_factors,
            base_value=None,
            confidence=None,  # Not an empirical ML probability
            explanation_summary="Multi-dimensional risk evaluated across weather, crop stage, and market dynamics.",
            xai_status=XAICapabilityStatus.HEURISTIC_ATTRIBUTION.value
        )
