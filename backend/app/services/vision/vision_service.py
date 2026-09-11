import io
import base64
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from PIL import Image

from app.services.vision.quality_gate import ImageQualityGate, ImageQualityGateResult
from app.services.vision.registry import VisionModelRegistry, DiseaseInfo
from app.services.vision.validator import VisionPredictionValidator, OODValidationResult
from app.services.safety.safety_engine import SafetyEngine
from app.services.voice.persona import BhoomiPersonaEngine
from app.services.voice.factory import get_voice_provider

logger = logging.getLogger(__name__)

class VisionAnalysisOutput(BaseModel):
    success: bool
    crop_identified: str
    disease_detected: str
    common_name: str
    confidence: float
    confidence_percentage: float
    uncertainty_level: str
    symptoms: List[str]
    ipm_recommendation: str
    chemical_treatment: str
    safety_advisories: List[str]
    quality_gate_metrics: Dict[str, Any]
    farmer_explanation: str
    spoken_explanation: str = ""
    assistant_audio_base64: Optional[str] = None
    requires_retake: bool = False
    rag_citations: List[Dict[str, Any]] = []
    rag_evidence: Optional[str] = None

class VisionService:
    """
    Modular Computer Vision Diagnostic Service.
    End-to-End Pipeline:
    Image -> Image Quality Gate -> Crop Identification -> Disease Classification
    -> OOD Validation -> Agronomic IPM Retrieval -> SafetyEngine Verification
    -> Persona Spoken Explanation -> Canonical TTS Audio Synthesis
    """

    @classmethod
    async def _synthesize_audio(cls, text: str, language: Optional[str] = "en") -> str:
        """Synthesizes text to speech using the canonical Sarvam TTS provider."""
        if not text:
            return ""
        try:
            provider = get_voice_provider()
            tts_res = await provider.synthesize(text=text, language_code=language or "en")
            if tts_res and tts_res.audio_bytes:
                return base64.b64encode(tts_res.audio_bytes).decode("utf-8")
        except Exception as e:
            logger.warning(f"[VISION_TTS] Audio synthesis failed: {e}")
        return ""

    @classmethod
    async def analyze_leaf_image(
        cls,
        image_bytes: bytes,
        crop_hint: Optional[str] = None,
        language: Optional[str] = "en",
        farmer_name: Optional[str] = None,
        synthesize_speech: bool = True
    ) -> VisionAnalysisOutput:
        active_lang = language or "en"

        # 1. Image Quality Gate Validation
        gate_result: ImageQualityGateResult = ImageQualityGate.validate(image_bytes)
        if not gate_result.is_valid:
            spoken = BhoomiPersonaEngine.format_vision_diagnosis(
                crop=crop_hint or "crop",
                disease_name="",
                confidence=0.0,
                is_rejected=True,
                rejection_reason=gate_result.reason,
                language=active_lang,
                farmer_name=farmer_name
            )
            audio_b64 = await cls._synthesize_audio(spoken, active_lang) if synthesize_speech else ""
            return VisionAnalysisOutput(
                success=False,
                crop_identified=crop_hint.title() if crop_hint else "Unknown",
                disease_detected="QUALITY_CHECK_FAILED",
                common_name="Image Quality Verification Failed",
                confidence=0.0,
                confidence_percentage=0.0,
                uncertainty_level="REJECTED",
                symptoms=[],
                ipm_recommendation="None",
                chemical_treatment="None",
                safety_advisories=[],
                quality_gate_metrics=gate_result.metrics,
                farmer_explanation=gate_result.farmer_advice,
                spoken_explanation=spoken,
                assistant_audio_base64=audio_b64,
                requires_retake=True
            )

        # 2. Crop Routing & Deep Learning Inference via CropModelRegistry
        from app.services.vision.crop_registry import CropModelRegistry
        canonical_crop = CropModelRegistry.normalize_crop_name(crop_hint)
        conflict_detected = False
        original_hint = canonical_crop

        pred = None
        # Attempt dedicated model if crop_hint was provided
        if canonical_crop:
            pred = CropModelRegistry.predict(image_bytes=image_bytes, crop_hint=canonical_crop)

        original_hint = canonical_crop
        conflict_detected = False

        # If crop_hint was not specified OR if dedicated prediction is below 0.80 confidence,
        # scan across all registered crop models to identify the best-matching pathology candidate
        if not pred or not pred.is_reliable or pred.is_ood or pred.quality_status == "FAILED" or pred.calibrated_confidence < 0.80:
            candidate = CropModelRegistry.identify_best_candidate(image_bytes=image_bytes)
            if candidate:
                detected_crop, candidate_pred = candidate
                if canonical_crop and canonical_crop != detected_crop:
                    # If candidate model has higher confidence or hinted model was weak
                    if not pred or not pred.is_reliable or candidate_pred.calibrated_confidence > (pred.calibrated_confidence + 0.08):
                        conflict_detected = True
                        logger.info("Vision crop conflict detected: requested=%s, detected=%s (candidate_conf=%.2f, hinted_conf=%.2f)",
                                    canonical_crop, detected_crop, candidate_pred.calibrated_confidence, pred.calibrated_confidence if pred else 0.0)
                        canonical_crop = detected_crop
                        pred = candidate_pred
                elif not canonical_crop:
                    canonical_crop = detected_crop
                    pred = candidate_pred

        # 3. Handle Low Confidence / OOD / Uncertain Crop
        if not pred or not pred.is_reliable or pred.is_ood or pred.quality_status == "FAILED":
            crop_label = (canonical_crop or "Crop").title() if canonical_crop else "Uncertain"
            spoken = (
                f"నమస్కారం, ఈ ఫోటోలో పంట లేదా తెగులును ఖచ్చితంగా గుర్తించలేకపోయాను. ఇది ఏ పంట ఫోటో? దయచేసి స్పష్టమైన ఫోటో తీసి పంపండి."
                if active_lang == "te" else (
                    f"नमस्ते, इस फोटो में फसल या बीमारी की पुष्टि नहीं हो सकी। यह किस फसल की फोटो है? कृपया एक और साफ फोटो भेजें।"
                    if active_lang == "hi" else (
                        f"Hello, I could not reliably determine the crop or diagnosis for this leaf photograph. Which crop is this image from? Please provide a clearer close-up photograph in good natural light."
                    )
                )
            )
            audio_b64 = await cls._synthesize_audio(spoken, active_lang) if synthesize_speech else ""
            return VisionAnalysisOutput(
                success=False,
                crop_identified=crop_label,
                disease_detected="CROP_UNCERTAIN",
                common_name="Crop Type / Lesion Pattern Uncertain",
                confidence=pred.calibrated_confidence if pred else 0.0,
                confidence_percentage=round((pred.calibrated_confidence if pred else 0.0) * 100, 1),
                uncertainty_level=pred.uncertainty_status if pred else "UNRELIABLE",
                symptoms=[],
                ipm_recommendation="Consult your local agricultural extension officer (KVK) or verify the crop type.",
                chemical_treatment="Do not spray unvetted chemicals without confirmed crop and disease diagnosis.",
                safety_advisories=["Model confidence is insufficient or input is out-of-distribution."],
                quality_gate_metrics=(pred.quality_metrics if pred else None) or gate_result.metrics,
                farmer_explanation=f"I could not reliably verify the diagnosis. Which crop is this image from? Please confirm your crop or capture a clearer photo of the affected leaf in daylight.",
                spoken_explanation=spoken,
                assistant_audio_base64=audio_b64,
                requires_retake=True
            )

        top_cand = pred.top_predictions[0] if pred.top_predictions else None
        disease_key = top_cand.disease_key if top_cand else "healthy"
        raw_conf = pred.calibrated_confidence

        ood_res = VisionPredictionValidator.evaluate(raw_conf, canonical_crop, disease_key)
        if not ood_res.is_in_distribution:
            spoken = BhoomiPersonaEngine.format_vision_diagnosis(
                crop=canonical_crop,
                disease_name="Uncertain Lesion Pattern",
                confidence=raw_conf,
                uncertainty_level=ood_res.uncertainty_level,
                language=active_lang,
                farmer_name=farmer_name
            )
            audio_b64 = await cls._synthesize_audio(spoken, active_lang)
            return VisionAnalysisOutput(
                success=False,
                crop_identified=canonical_crop.title(),
                disease_detected="UNCERTAIN_ANOMALY",
                common_name="Uncertain Lesion Pattern",
                confidence=raw_conf,
                confidence_percentage=round(raw_conf * 100, 1),
                uncertainty_level=ood_res.uncertainty_level,
                symptoms=[],
                ipm_recommendation="Consult local agricultural university / KVK extension officer.",
                chemical_treatment="Do not spray unvetted chemicals without confirmed diagnosis.",
                safety_advisories=[ood_res.warning or "Low Confidence Alert"],
                quality_gate_metrics=gate_result.metrics,
                farmer_explanation=ood_res.advisory,
                spoken_explanation=spoken,
                assistant_audio_base64=audio_b64,
                requires_retake=True
            )

        # 5. Retrieve Pathology & IPM Treatment from Knowledge Registry & RAG (Step 45)
        disease_info: Optional[DiseaseInfo] = VisionModelRegistry.get_disease_info(canonical_crop, disease_key)
        if not disease_info:
            disease_info = VisionModelRegistry.get_disease_info(canonical_crop, "healthy")
        if not disease_info:
            crop_tax = VisionModelRegistry.CROP_TAXONOMY.get(canonical_crop, {})
            disease_info = next(iter(crop_tax.values())) if crop_tax else DiseaseInfo(
                disease_id=f"{canonical_crop}_{disease_key}",
                common_name=pred.common_name,
                pathogen_type="fungal",
                symptoms=["Foliar lesions observed on leaf blade"],
                ipm_treatment="Monitor field closely and consult local KVK agronomy advisory.",
                chemical_treatment="Apply recommended bio-protectant if symptoms spread.",
                prevention_advisory="Ensure proper crop spacing and adequate field drainage."
            )

        # Step 45: Image + RAG Parity - Query verified RAG guidance for predicted crop and disease
        rag_citations: List[Dict[str, Any]] = []
        rag_evidence_text: Optional[str] = None
        try:
            from app.services.rag.rag_service import AgriculturalRAGService, RAGQueryInput
            rag_res = AgriculturalRAGService.search(RAGQueryInput(
                query=f"{canonical_crop} {disease_info.common_name} management control",
                crop=canonical_crop,
                top_k=2
            ))
            if rag_res.evidence_found:
                rag_evidence_text = rag_res.grounded_summary
                rag_citations = [c.model_dump() for c in rag_res.citations]
        except Exception as e:
            logger.debug(f"Vision RAG enrichment skipped ({e})")

        # 6. SafetyEngine Guardrails Verification
        safety_eval = SafetyEngine.evaluate(
            recommendation_text=f"{disease_info.chemical_treatment} | {disease_info.ipm_treatment}",
            crop=canonical_crop,
            stage="vegetative"
        )

        all_warnings = list(safety_eval.warnings)
        if ood_res.warning:
            all_warnings.append(ood_res.warning)

        safety_blocked = False
        chem_treatment = disease_info.chemical_treatment
        if safety_eval.status == "BLOCK":
            safety_blocked = True
            chem_treatment = safety_eval.modified_text or "Chemical treatment blocked by SafetyEngine."
            all_warnings.extend(safety_eval.blocked_reasons)

        # 7. Generate Spoken Explanation via BhoomiPersonaEngine
        spoken = BhoomiPersonaEngine.format_vision_diagnosis(
            crop=canonical_crop,
            disease_name=disease_info.disease_id,
            confidence=raw_conf,
            ipm_action=disease_info.ipm_treatment,
            chemical_treatment=chem_treatment,
            safety_advisories=all_warnings,
            is_rejected=False,
            uncertainty_level=ood_res.uncertainty_level,
            safety_blocked=safety_blocked,
            safety_blocked_reason=safety_eval.blocked_reasons[0] if safety_eval.blocked_reasons else "",
            language=active_lang,
            farmer_name=farmer_name
        )
        audio_b64 = await cls._synthesize_audio(spoken, active_lang) if synthesize_speech else ""

        # 8. Visual Farmer-friendly explanation
        conflict_prefix = ""
        if conflict_detected and original_hint and original_hint != canonical_crop:
            conflict_prefix = (
                f"**Crop Notice**: The uploaded image appears inconsistent with your registered {original_hint.title()} crop context. "
                f"Visual patterns match **{canonical_crop.title()}**. Please confirm if this leaf is from {canonical_crop.title()}.\n\n"
            )
            all_warnings.append(f"Image visual features match {canonical_crop.title()}, conflicting with registered {original_hint.title()} crop.")

        if safety_blocked:
            explanation = (
                f"{conflict_prefix}Diagnosis: Detected **{disease_info.common_name}** with {round(raw_conf * 100, 1)}% confidence. "
                f"Safety Notice: {safety_eval.modified_text} "
                f"Eco-Friendly Action: {disease_info.ipm_treatment}."
            )
        elif disease_info.pathogen_type == "healthy":
            explanation = (
                f"{conflict_prefix}Great news! Your {canonical_crop.title()} leaf appears healthy with robust green pigmentation "
                f"({round(raw_conf * 100, 1)}% confidence). Continue regular farm monitoring."
            )
        else:
            explanation = (
                f"{conflict_prefix}Diagnosis: Detected **{disease_info.common_name}** with {round(raw_conf * 100, 1)}% confidence. "
                f"Immediate Action: {disease_info.ipm_treatment} "
                f"Chemical Option: {chem_treatment}."
            )

        return VisionAnalysisOutput(
            success=not safety_blocked,
            crop_identified=canonical_crop.title(),
            disease_detected=disease_info.disease_id,
            common_name=disease_info.common_name,
            confidence=round(raw_conf, 4),
            confidence_percentage=round(raw_conf * 100, 1),
            uncertainty_level=ood_res.uncertainty_level,
            symptoms=disease_info.symptoms,
            ipm_recommendation=disease_info.ipm_treatment,
            chemical_treatment=chem_treatment,
            safety_advisories=all_warnings,
            quality_gate_metrics=gate_result.metrics,
            farmer_explanation=explanation,
            spoken_explanation=spoken,
            assistant_audio_base64=audio_b64,
            requires_retake=False,
            rag_citations=rag_citations,
            rag_evidence=rag_evidence_text
        )
