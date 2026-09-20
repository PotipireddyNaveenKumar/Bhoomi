import uuid
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone

from app.services.xai.explanation_model import (
    ExplanationResult,
    ModelExplanation,
    VisionHeatmapExplanation,
    RAGEvidenceExplanation,
    LiveDataExplanation,
    FeatureContribution,
    XAICapabilityStatus
)
from app.services.xai.shap_explainer import TabularSHAPExplainer
from app.services.xai.gradcam_explainer import DiseaseGradCAMExplainer
from app.services.xai.localization import XAILocalizationService
from app.services.rag.evidence_model import (
    EvidenceStatus,
    CanonicalEvidenceItem,
    CanonicalSourceCitation
)
from app.schemas.market import MarketFreshnessStatus
from app.schemas.weather import FreshnessStatus

logger = logging.getLogger(__name__)


class XAIService:
    """
    Central Explainable AI (XAI) Orchestrator for BHOOMI V2.
    Harmonizes:
    - Tabular TreeSHAP Explanations (Crop, Yield, Fertilizer)
    - Convolutional Grad-CAM Attributions (Foliar Disease Vision)
    - Batch 6 Evidence-Grounded Citations (Authority Tiers, Sufficiency Gates)
    - Batch 4 Live Data Provenance (Weather & Market Freshness Guarantees)
    - Multilingual Farmer-Facing Translations (en, te, hi, ta, kn, ml)
    """

    @classmethod
    def create_rag_explanation(
        cls,
        evidence_status: Union[str, EvidenceStatus],
        evidence_items: Optional[List[CanonicalEvidenceItem]] = None,
        citations: Optional[List[CanonicalSourceCitation]] = None,
        lang: str = "en"
    ) -> RAGEvidenceExplanation:
        """
        Builds auditable RAG evidence explanation.
        If status is INSUFFICIENT or UNAVAILABLE, clearly states so without fabricating citations.
        """
        status_val = evidence_status.value if isinstance(evidence_status, EvidenceStatus) else str(evidence_status)
        is_sufficient = (status_val == EvidenceStatus.SUFFICIENT.value)

        retrieved_list = []
        if evidence_items:
            for item in evidence_items:
                retrieved_list.append(item.model_dump() if hasattr(item, "model_dump") else dict(item))

        cites = citations or []
        citation_ids = [c.citation_id for c in cites]

        if not is_sufficient:
            summary = XAILocalizationService.get_label("insufficient_evidence", lang)
        else:
            auth_names = ", ".join(list(set([c.authority for c in cites if c.authority])))
            summary = f"Grounded in verified agronomic research from {auth_names}." if auth_names else "Grounded in verified agronomic research."

        return RAGEvidenceExplanation(
            evidence_status=status_val,
            retrieved_evidence=retrieved_list,
            citation_identifiers=citation_ids,
            citations=cites,
            explanation_summary=summary,
            is_sufficient=is_sufficient
        )

    @classmethod
    def create_live_data_explanation(
        cls,
        weather_res: Optional[Any] = None,
        market_res: Optional[Any] = None,
        lang: str = "en"
    ) -> LiveDataExplanation:
        """
        Builds live data provenance explanation preserving Batch 4 fail-safe semantics:
        - CURRENT: Live provider successfully queried, data fresh, is_synthetic=False
        - STALE: Provider cached data older than fresh window, is_synthetic=False
        - UNAVAILABLE: Provider failed or unconfigured, data fields null/absent, is_synthetic=False
        - DEMO / SYNTHETIC: Explicit demo or test mode only, is_synthetic=True
        """
        if weather_res:
            w_fresh = getattr(weather_res, "freshness", None) or getattr(getattr(weather_res, "current", None), "freshness", "UNAVAILABLE")
            w_src = getattr(weather_res, "source", None) or getattr(getattr(weather_res, "current", None), "source", "Open-Meteo / IMD")
            # Strictly determine synthetic: true ONLY for explicit DEMO or SYNTHETIC mock modes
            is_syn = getattr(weather_res, "is_synthetic", False) or (
                str(w_fresh).upper() in [FreshnessStatus.DEMO.value, FreshnessStatus.SYNTHETIC.value, "DEMO", "SYNTHETIC"]
            )
            weather_dict = {
                "provider": str(w_src),
                "freshness": str(w_fresh),
                "is_synthetic": is_syn,
                "observed_at": getattr(getattr(weather_res, "current", None), "observed_at", None),
                "contribution_status": "CURRENT" if str(w_fresh).upper() in [FreshnessStatus.CURRENT.value, "CURRENT", "ACTIVE"] else str(w_fresh)
            }
        else:
            weather_dict = {
                "provider": "None",
                "freshness": "UNAVAILABLE",
                "is_synthetic": False,
                "observed_at": None,
                "contribution_status": "UNAVAILABLE"
            }

        if market_res:
            m_fresh = getattr(market_res, "freshness", None) or "UNAVAILABLE"
            m_source = getattr(market_res, "source", None) or "AGMARKNET / data.gov.in"
            # Strictly determine synthetic: true ONLY for explicit DEMO or SYNTHETIC mock modes
            is_syn = getattr(market_res, "is_synthetic", False) or (
                str(m_fresh).upper() in [MarketFreshnessStatus.DEMO.value, MarketFreshnessStatus.SYNTHETIC.value, "DEMO", "SYNTHETIC"]
            )
            market_dict = {
                "provider": str(m_source),
                "freshness": str(m_fresh),
                "is_synthetic": is_syn,
                "observed_at": getattr(market_res, "retrieved_at", None),
                "contribution_status": "CURRENT" if str(m_fresh).upper() in [MarketFreshnessStatus.CURRENT.value, "CURRENT", "ACTIVE"] else str(m_fresh)
            }
        else:
            market_dict = {
                "provider": "None",
                "freshness": "UNAVAILABLE",
                "is_synthetic": False,
                "observed_at": None,
                "contribution_status": "UNAVAILABLE"
            }

        w_status = weather_dict["contribution_status"]
        m_status = market_dict["contribution_status"]

        summary = f"Weather: {w_status} | Market: {m_status}"
        return LiveDataExplanation(
            weather=weather_dict,
            market=market_dict,
            summary=summary
        )

    @classmethod
    def explain_crop_recommendation(
        cls,
        input_data: Any,
        prediction_output: Any,
        evidence_items: Optional[List[CanonicalEvidenceItem]] = None,
        citations: Optional[List[CanonicalSourceCitation]] = None,
        evidence_status: Union[str, EvidenceStatus] = EvidenceStatus.SUFFICIENT,
        weather_res: Optional[Any] = None,
        market_res: Optional[Any] = None,
        lang: str = "en"
    ) -> ExplanationResult:
        """
        Builds canonical ExplanationResult for Crop Recommendation using actual SHAP values.
        """
        model_exp = TabularSHAPExplainer.explain_crop_recommendation(input_data, prediction_output)
        rag_exp = cls.create_rag_explanation(evidence_status, evidence_items, citations, lang=lang)
        live_exp = cls.create_live_data_explanation(weather_res, market_res, lang=lang)

        # Bullets for farmer
        why_bullets = []
        for f in model_exp.top_positive_factors[:2]:
            why_bullets.append(f"{f.display_name or f.feature} ({f.value}) strongly supported {model_exp.prediction}.")

        ev_bullets = []
        if rag_exp.is_sufficient and rag_exp.citations:
            for c in rag_exp.citations[:2]:
                ev_bullets.append(f"{c.authority} - {c.document_title} ({c.section or 'General'})")
        elif not rag_exp.is_sufficient:
            ev_bullets.append(rag_exp.explanation_summary)

        w_str = live_exp.weather["contribution_status"] if live_exp.weather else "UNAVAILABLE"
        m_str = live_exp.market["contribution_status"] if live_exp.market else "UNAVAILABLE"

        limitations = []
        if getattr(prediction_output, "warnings", []):
            limitations.extend(prediction_output.warnings)
        if not rag_exp.is_sufficient:
            limitations.append("Agricultural research citations are insufficient for complete validation.")
        if w_str in ["STALE", "UNAVAILABLE", "DEMO"]:
            limitations.append(f"Live weather data is {w_str}; local field validation advised.")

        primary_crop = prediction_output.recommended_crops[0].crop if (prediction_output and prediction_output.recommended_crops) else "Crop"

        return ExplanationResult(
            decision_id=f"dec_crop_{uuid.uuid4().hex[:8]}",
            decision_type="crop_recommendation",
            prediction=primary_crop,
            model_name=model_exp.model_name,
            model_version=model_exp.model_version,
            xai_status=model_exp.xai_status,
            model_explanation=model_exp,
            vision_explanation=None,
            rag_evidence=rag_exp,
            live_data=live_exp,
            top_factors=model_exp.top_positive_factors,
            citations=rag_exp.citations,
            confidence=model_exp.confidence,
            why_summary="\n".join([f"- {b}" for b in why_bullets]) if why_bullets else model_exp.explanation_summary,
            evidence_summary=rag_exp.explanation_summary,
            current_data_summary=live_exp.summary,
            limitations=limitations,
            locale=lang,
            generated_at=datetime.now(timezone.utc).isoformat()
        )

    @classmethod
    def explain_yield_prediction(
        cls,
        input_data: Any,
        prediction_output: Any,
        evidence_items: Optional[List[CanonicalEvidenceItem]] = None,
        citations: Optional[List[CanonicalSourceCitation]] = None,
        evidence_status: Union[str, EvidenceStatus] = EvidenceStatus.SUFFICIENT,
        weather_res: Optional[Any] = None,
        market_res: Optional[Any] = None,
        lang: str = "en"
    ) -> ExplanationResult:
        """
        Builds canonical ExplanationResult for Yield Prediction using actual SHAP values.
        """
        model_exp = TabularSHAPExplainer.explain_yield_prediction(input_data, prediction_output)
        rag_exp = cls.create_rag_explanation(evidence_status, evidence_items, citations, lang=lang)
        live_exp = cls.create_live_data_explanation(weather_res, market_res, lang=lang)

        CONVERSION_T_HA_TO_Q_ACRE = 4.04686
        why_bullets = []
        for f in model_exp.top_positive_factors[:2]:
            s_conv = abs(f.shap_value * CONVERSION_T_HA_TO_Q_ACRE)
            why_bullets.append(f"{f.display_name or f.feature} ({f.value}) positively drove yield (+{abs(f.shap_value):.2f} t/ha / +{s_conv:.2f} quintals/acre).")

        ev_bullets = []
        if rag_exp.is_sufficient and rag_exp.citations:
            for c in rag_exp.citations[:2]:
                ev_bullets.append(f"{c.authority}: {c.document_title}")
        elif not rag_exp.is_sufficient:
            ev_bullets.append(rag_exp.explanation_summary)

        w_str = live_exp.weather["contribution_status"] if live_exp.weather else "UNAVAILABLE"
        m_str = live_exp.market["contribution_status"] if live_exp.market else "UNAVAILABLE"

        limitations = list(getattr(prediction_output, "warnings", []))
        if w_str in ["STALE", "UNAVAILABLE"]:
            limitations.append("Rainfall assumptions rely on historical baseline without verified live weather.")

        native_t_ha = getattr(prediction_output, "predicted_yield_tons_per_hectare", round(prediction_output.predicted_yield_quintals_per_acre / CONVERSION_T_HA_TO_Q_ACRE, 2))
        return ExplanationResult(
            decision_id=f"dec_yield_{uuid.uuid4().hex[:8]}",
            decision_type="yield_prediction",
            prediction=f"{prediction_output.predicted_yield_quintals_per_acre} quintals/acre ({native_t_ha} t/ha)",
            model_name=model_exp.model_name,
            model_version=model_exp.model_version,
            xai_status=model_exp.xai_status,
            model_explanation=model_exp,
            vision_explanation=None,
            rag_evidence=rag_exp,
            live_data=live_exp,
            top_factors=model_exp.top_positive_factors,
            citations=rag_exp.citations,
            confidence=None,  # Legitimate: interval [ci_low, ci_high] in prediction_output
            why_summary="\n".join([f"- {b}" for b in why_bullets]) if why_bullets else model_exp.explanation_summary,
            evidence_summary=rag_exp.explanation_summary,
            current_data_summary=live_exp.summary,
            limitations=limitations,
            locale=lang,
            generated_at=datetime.now(timezone.utc).isoformat()
        )

    @classmethod
    def explain_vision_diagnosis(
        cls,
        image_bytes: bytes,
        crop_hint: Optional[str] = "tomato",
        evidence_items: Optional[List[CanonicalEvidenceItem]] = None,
        citations: Optional[List[CanonicalSourceCitation]] = None,
        evidence_status: Union[str, EvidenceStatus] = EvidenceStatus.SUFFICIENT,
        weather_res: Optional[Any] = None,
        lang: str = "en"
    ) -> ExplanationResult:
        """
        Builds canonical ExplanationResult for Leaf Pathology Diagnosis using Grad-CAM.
        """
        vision_exp = DiseaseGradCAMExplainer.explain_leaf_diagnosis(image_bytes, crop_hint=crop_hint)
        rag_exp = cls.create_rag_explanation(evidence_status, evidence_items, citations, lang=lang)
        live_exp = cls.create_live_data_explanation(weather_res=weather_res, market_res=None, lang=lang)

        why_bullets = []
        if vision_exp.xai_status == XAICapabilityStatus.AVAILABLE.value:
            peak = vision_exp.localization_metadata.get("peak_cell", [0, 0])
            area = vision_exp.localization_metadata.get("high_activation_area_ratio", 0.0)
            why_bullets.append(f"Model convolutional activations focused on lesion pattern at grid {peak} ({area*100:.1f}% hotspot concentration).")
        else:
            why_bullets.append(f"Grad-CAM explanation status: {vision_exp.xai_status}.")

        limitations = list(vision_exp.limitations)
        if vision_exp.xai_status != XAICapabilityStatus.AVAILABLE.value:
            limitations.append("Grad-CAM visualization unavailable for this model or input.")

        return ExplanationResult(
            decision_id=f"dec_vision_{uuid.uuid4().hex[:8]}",
            decision_type="disease_vision",
            prediction=vision_exp.predicted_disease,
            model_name=vision_exp.model_identifier,
            model_version=vision_exp.model_version,
            xai_status=vision_exp.xai_status,
            model_explanation=None,
            vision_explanation=vision_exp,
            rag_evidence=rag_exp,
            live_data=live_exp,
            top_factors=[],
            citations=rag_exp.citations,
            confidence=vision_exp.confidence,
            why_summary="\n".join([f"- {b}" for b in why_bullets]),
            evidence_summary=rag_exp.explanation_summary,
            current_data_summary=live_exp.summary,
            limitations=limitations,
            locale=lang,
            generated_at=datetime.now(timezone.utc).isoformat()
        )


BhoomiXAIService = XAIService
