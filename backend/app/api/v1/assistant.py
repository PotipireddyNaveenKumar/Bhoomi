import base64
import logging
import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.models.chat import ChatMessage
from app.agents.orchestrator import BhoomiAgentOrchestrator
from app.repositories.chat_repo import ChatRepository
from app.services.vision.vision_service import VisionService
from app.services.farm_manager.recommendation_trace import RecommendationTraceStore, FeedbackStatus
from app.services.memory.farm_memory_v2 import FarmMemoryV2, ProvenanceType
from app.services.monitoring.model_monitor import ModelMonitoringService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["Multimodal AI Assistant"])

class AssistantChatRequest(BaseModel):
    message: str = Field(..., description="Farmer's natural language query")
    session_id: Optional[str] = Field(default="default_session", description="Session identifier for multi-turn history")
    language_code: Optional[str] = Field(default="en", description="Language code: en, te, hi, ta, kn, mr")
    language: Optional[str] = None
    image_base64: Optional[str] = Field(default=None, description="Optional base64-encoded leaf photograph")
    farm_id: Optional[str] = None

class AssistantChatResponse(BaseModel):
    status: str = "success"
    session_id: str
    reply_text: str
    language_code: str
    intent: str
    agents_invoked: List[str]
    structured_data: Dict[str, Any]
    visual_cards: List[Dict[str, Any]] = []
    assistant_audio_base64: Optional[str] = None
    visual_xai_base64: Optional[str] = None
    execution_trace: List[Dict[str, Any]] = []

@router.post("/chat", response_model=AssistantChatResponse)
async def chat_with_assistant(
    req: AssistantChatRequest,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    target_lang = (req.language if req.language and req.language_code == "en" else req.language_code) or req.language or farmer.preferred_language or "en"
    session_id = req.session_id or "default_session"
    user_query = req.message.strip()
    agents_invoked = ["orchestrator"]
    structured_data: Dict[str, Any] = {}
    visual_cards: List[Dict[str, Any]] = []
    assistant_audio_base64: Optional[str] = None
    reply = ""

    # 1. Handle image analysis if image_base64 is attached (Thin fallback to Phase 3 vision pipeline)
    if req.image_base64:
        try:
            raw_b64 = req.image_base64
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)

            # Auto-upscale small crops or low-res web uploads so they meet quality gates
            try:
                from PIL import Image
                import io
                with Image.open(io.BytesIO(img_bytes)) as pil_img:
                    if pil_img.width < 256 or pil_img.height < 256:
                        scale = max(256 / max(pil_img.width, 1), 256 / max(pil_img.height, 1))
                        new_w = max(256, int(pil_img.width * scale))
                        new_h = max(256, int(pil_img.height * scale))
                        resized = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                        buf = io.BytesIO()
                        resized.convert("RGB").save(buf, format="JPEG", quality=95)
                        img_bytes = buf.getvalue()
            except Exception:
                pass

            # Infer crop hint from query text or farmer digital twin
            crop_hint = None
            from app.services.vision.crop_registry import CROP_ALIASES, CropModelRegistry
            msg_lower = user_query.lower()
            for alias, canonical in CROP_ALIASES.items():
                if alias in msg_lower:
                    crop_hint = canonical
                    break
            if not crop_hint:
                from app.services.memory.digital_twin import DigitalTwinService
                farmer_ctx = await DigitalTwinService.get_farmer_context(db, farmer.id)
                if farmer_ctx and farmer_ctx.active_crops and farmer_ctx.active_crops[0].get("crop_name"):
                    crop_hint = CropModelRegistry.normalize_crop_name(farmer_ctx.active_crops[0].get("crop_name"))
                elif getattr(farmer, "current_crop", None):
                    crop_hint = CropModelRegistry.normalize_crop_name(farmer.current_crop)
                else:
                    crop_hint = None

            # Invoke canonical Phase 3 VisionService with farmer's target language
            vision_res = await VisionService.analyze_leaf_image(img_bytes, crop_hint=crop_hint, language=target_lang)
            agents_invoked.append("vision_cnn")
            structured_data["vision_diagnosis"] = vision_res.model_dump()

            # The spoken explanation generated by BhoomiPersonaEngine is the canonical plain-language response
            reply = vision_res.spoken_explanation or vision_res.farmer_explanation or "Leaf image analyzed."
            if vision_res.assistant_audio_base64:
                assistant_audio_base64 = vision_res.assistant_audio_base64

            # Attach rich visual card for chat UI
            visual_card_item = {
                "card_type": "crop_health_card",
                "title": f"Leaf Diagnosis: {vision_res.crop_identified} - {vision_res.common_name}",
                "data": vision_res.model_dump()
            }
            visual_cards.append(visual_card_item)
            structured_data["visual_cards"] = visual_cards

        except Exception as e:
            logger.warning(f"Error analyzing base64 image in assistant chat: {e}")
            reply = (
                "నమస్కారం, మీ ఆకు ఫోటోను విశ్లేషించడంలో అంతర్గత లోపం ఏర్పడింది. దయచేసి మళ్లీ ప్రయత్నించండి."
                if target_lang == "te" else (
                    "नमस्ते, आपकी पत्ती के फोटो का विश्लेषण करने में समस्या आई। कृपया पुनः प्रयास करें।"
                    if target_lang == "hi" else "I encountered an error analyzing your leaf photograph. Please try again."
                )
            )

    # 2. Handle plain text question through canonical BhoomiAgentOrchestrator
    else:
        try:
            orch_res = await BhoomiAgentOrchestrator.process_turn(
                db=db,
                farmer_id=farmer.id,
                session_id=session_id,
                user_text=user_query,
                input_mode="text",
                language=target_lang
            )
            reply = orch_res.response_text
            if orch_res.visual_cards:
                visual_cards = orch_res.visual_cards
                structured_data["visual_cards"] = visual_cards
        except Exception as e:
            logger.error(f"Orchestration failure: {e}", exc_info=True)
            reply = (
                "నమస్కారం, మీ ప్రశ్నకు సమాధానం ఇవ్వడంలో అంతర్గత లోపం ఏర్పడింది. దయచేసి మళ్లీ ప్రయత్నించండి."
                if target_lang == "te" else (
                    "नमस्ते, आपके प्रश्न का उत्तर देने में समस्या आई। कृपया पुनः प्रयास करें।"
                    if target_lang == "hi" else "I encountered an error processing your query. Please try again."
                )
            )

    # 3. Save Assistant Message to ChatRepository history
    try:
        chat_repo = ChatRepository(db)
        session = await chat_repo.get_or_create_session(
            farmer.id,
            session_id=session_id,
            language=target_lang
        )
        await chat_repo.save_message(
            session_id=session.id,
            sender="user",
            content=user_query,
            input_mode="text",
            image_url=None,
        )
        await chat_repo.save_message(
            session_id=session.id,
            sender="assistant",
            content=reply,
            input_mode="text",
            structured_payload={"visual_cards": visual_cards} if visual_cards else None,
        )
    except Exception as e:
        logger.warning(f"Error saving chat turn in assistant.py: {e}")

    return AssistantChatResponse(
        status="success",
        session_id=session_id,
        reply_text=reply,
        language_code=target_lang,
        intent="agronomic_advisory",
        agents_invoked=agents_invoked,
        structured_data=structured_data,
        visual_cards=visual_cards,
        assistant_audio_base64=assistant_audio_base64,
        execution_trace=[{"trace_id": getattr(orch_res, "trace_id", "") if 'orch_res' in locals() else ""}]
    )

@router.post("/chat-upload", response_model=AssistantChatResponse)
async def chat_with_image_upload(
    message: str = Form(default="Analyze this crop problem"),
    session_id: str = Form(default="default_session"),
    language_code: str = Form(default="en"),
    file: Optional[UploadFile] = File(default=None),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    img_b64 = None
    if file:
        content = await file.read()
        img_b64 = base64.b64encode(content).decode("utf-8")

    req = AssistantChatRequest(
        message=message,
        session_id=session_id,
        language_code=language_code,
        image_base64=img_b64
    )
    return await chat_with_assistant(req, farmer=farmer, db=db)

@router.get("/sessions")
async def list_chat_sessions(
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = ChatRepository(db)
    sessions = await repo.get_farmer_sessions(farmer.id)
    return sessions

@router.get("/sessions/{session_id}")
async def get_session_history(
    session_id: str,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = ChatRepository(db)
    session = await repo.get_or_create_session(farmer.id, session_id=session_id)
    return session


class AssistantFeedbackRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Chat session identifier")
    rating: str = Field(..., description="Farmer feedback: 'helpful' or 'not_helpful'")
    response_text: Optional[str] = Field(default=None, description="Excerpt of the assistant response being rated")
    language_code: Optional[str] = Field(default="en", description="Language code: en, te, hi, ta, kn, ml")


class AssistantFeedbackResponse(BaseModel):
    status: str = "success"
    rating: str
    trace_updated: bool = False
    memory_recorded: bool = False


@router.post("/feedback", response_model=AssistantFeedbackResponse)
async def submit_assistant_feedback(
    req: AssistantFeedbackRequest,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    """
    Submits farmer feedback on AI assistant responses.
    Validates input and records through existing persistence mechanisms:
    1. Relational DB (ChatMessage metadata_json)
    2. RecommendationTraceStore (Audit & Explainability trace)
    3. FarmMemoryV2 (Episodic farmer feedback)
    4. ModelMonitoringService (Aggregated quality metrics)
    """
    # 1. Validate rating
    rating_norm = req.rating.lower().strip()
    if rating_norm not in ("helpful", "not_helpful"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid rating. Allowed values: 'helpful', 'not_helpful'."
        )

    # 2. Validate language_code when supplied
    valid_langs = {"en", "te", "hi", "ta", "kn", "ml"}
    lang_norm = (req.language_code or "en").split("-")[0].lower().strip()
    if lang_norm and lang_norm not in valid_langs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid language_code '{req.language_code}'. Allowed: {', '.join(sorted(valid_langs))}."
        )

    # 3. Relational DB: Associate with farmer session and update latest assistant message
    chat_repo = ChatRepository(db)
    session = await chat_repo.get_or_create_session(farmer.id, session_id=req.session_id, language=lang_norm)

    msg_query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id, ChatMessage.sender == "assistant")
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    msg_res = await db.execute(msg_query)
    latest_msg = msg_res.scalars().first()
    if latest_msg:
        meta = dict(latest_msg.metadata_json or {})
        meta["feedback_rating"] = rating_norm
        meta["feedback_timestamp"] = datetime.now(timezone.utc).isoformat()
        latest_msg.metadata_json = meta
        await db.commit()

    # 4. RecommendationTraceStore: Update latest decision trace for this farmer
    trace_updated = False
    try:
        farmer_traces = RecommendationTraceStore.list_for_farmer(farmer.id)
        if farmer_traces:
            latest_trace = farmer_traces[-1]
            RecommendationTraceStore.update_feedback(
                recommendation_id=latest_trace.recommendation_id,
                farmer_action=FeedbackStatus.FOLLOWED if rating_norm == "helpful" else FeedbackStatus.NOT_FOLLOWED,
                feedback_rating=FeedbackStatus.HELPFUL if rating_norm == "helpful" else FeedbackStatus.NOT_HELPFUL,
                feedback_notes=f"Farmer chat feedback: {rating_norm}"
            )
            trace_updated = True
    except Exception as e:
        logger.warning(f"Could not update RecommendationTraceStore: {e}")

    # 5. FarmMemoryV2: Record episodic farmer feedback
    memory_recorded = False
    try:
        FarmMemoryV2.add_memory(
            farmer_id=farmer.id,
            category="FEEDBACK",
            key=f"chat_feedback_{session.id}_{int(time.time())}",
            value={
                "session_id": session.id,
                "rating": rating_norm,
                "language_code": lang_norm,
                "response_snippet": (req.response_text or "")[:150]
            },
            provenance=ProvenanceType.FARMER_ACTION
        )
        memory_recorded = True
    except Exception as e:
        logger.warning(f"Could not record FarmMemoryV2 entry: {e}")

    # 6. ModelMonitoringService: Quality metrics
    try:
        rating_key = "USEFUL" if rating_norm == "helpful" else "NOT_USEFUL"
        ModelMonitoringService.record_model_feedback("assistant_chat", rating_key)
    except Exception:
        pass

    logger.info(f"Feedback recorded successfully for farmer {farmer.id}: rating={rating_norm}")
    return AssistantFeedbackResponse(
        status="success",
        rating=rating_norm,
        trace_updated=trace_updated,
        memory_recorded=memory_recorded
    )
