import base64
import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_farmer_profile, get_current_farmer_profile_optional
from app.models.farmer import FarmerProfile
from app.services.voice.factory import get_voice_provider
from app.services.voice.sarvam import SarvamVoiceProvider
from app.repositories.chat_repo import ChatRepository
from app.agents.orchestrator import BhoomiAgentOrchestrator
from app.schemas.voice import (
    TranscriptionResponse,
    SynthesisRequest,
    SynthesisResponse,
    VoiceInteractResponse,
    VoiceTaskActionRequest,
    VoiceTaskActionResponse
)
from app.services.voice.confirmation_state import ConfirmationStateMachine, ConfirmationState
from app.services.voice.intent_service import IntentNormalizationService
from app.core.exceptions import VoiceProcessingException

logger = logging.getLogger(__name__)

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            safe_args = [str(a).encode("ascii", "backslashreplace").decode("ascii") for a in args]
            print(*safe_args, **kwargs)
        except Exception:
            pass

router = APIRouter(prefix="/voice", tags=["Voice Engine (Sarvam / Multi-provider)"])

MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_AUDIO_MIME_PREFIXES = ("audio/", "application/octet-stream", "video/webm")
ALLOWED_AUDIO_EXTENSIONS = (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".webm", ".flac")

FALLBACK_PROMPTS = {
    "te": "నమస్కారం, మీ మాట స్పష్టంగా వినిపించలేదు. దయచేసి మళ్లీ చెప్పండి.",
    "hi": "नमस्ते, आपकी आवाज़ साफ़ नहीं आई। कृपया दोबारा बोलें।",
    "ta": "வணக்கம், உங்கள் குரல் தெளிவாகக் கேட்கவில்லை. தயவுசெய்து மீண்டும் பேசுங்கள்.",
    "kn": "ನಮಸ್ಕಾರ, ನಿಮ್ಮ ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ಮಾತನಾಡಿ.",
    "ml": "നമസ്കാരം, നിങ്ങളുടെ ശബ്ദം വ്യക്തമായി കേട്ടില്ല. ദയവായി വീണ്ടും പറയുക.",
    "en": "Hello, I couldn't hear you clearly. Please try speaking again."
}

def validate_audio_file(file: UploadFile) -> None:
    """Validates audio file MIME type and extension to prevent malicious uploads."""
    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()
    
    is_valid_mime = any(content_type.startswith(prefix) for prefix in ALLOWED_AUDIO_MIME_PREFIXES)
    is_valid_ext = any(filename.endswith(ext) for ext in ALLOWED_AUDIO_EXTENSIONS)
    
    if not (is_valid_mime or is_valid_ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{content_type}'. Supported formats: WAV, MP3, M4A, OGG, WebM."
        )

async def read_audio_payload(file: UploadFile) -> bytes:
    """Safely reads audio payload enforcing strict file size boundaries."""
    validate_audio_file(file)
    audio_bytes = await file.read()
    
    if not audio_bytes or len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty (0 bytes)."
        )
        
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file exceeds maximum size of {MAX_AUDIO_SIZE // (1024 * 1024)}MB."
        )
        
    return audio_bytes

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language_code: str = Form(default="auto"),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
):
    audio_bytes = await read_audio_payload(file)
    provider = get_voice_provider()
    target_lang = language_code if language_code != "auto" else (farmer.preferred_language or "en")
    
    try:
        res = await provider.transcribe(audio_bytes=audio_bytes, language_code=target_lang)
        return TranscriptionResponse(
            text=res.text,
            language_code=res.language_code,
            confidence=res.confidence,
            provider=res.provider
        )
    except VoiceProcessingException as exc:
        err_msg = exc.detail.get("error", {}).get("message", str(exc)) if isinstance(exc.detail, dict) else str(exc)
        logger.warning(f"Transcription failed: {err_msg}")
        raise exc

@router.post("/synthesize")
async def synthesize_speech(
    req: SynthesisRequest,
    farmer: Optional[FarmerProfile] = Depends(get_current_farmer_profile_optional),
):
    provider = get_voice_provider()
    lang = req.language_code or (farmer.preferred_language if farmer else "en")
    
    try:
        res = await provider.synthesize(text=req.text, language_code=lang, speaker_gender=req.speaker_gender)
        return Response(content=res.audio_bytes, media_type=res.content_type)
    except VoiceProcessingException as exc:
        err_msg = exc.detail.get("error", {}).get("message", str(exc)) if isinstance(exc.detail, dict) else str(exc)
        logger.warning(f"Synthesis failed: {err_msg}")
        raise exc

@router.post("/interact", response_model=VoiceInteractResponse)
async def voice_interact(
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
    language: Optional[str] = Form(default=None),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified Voice Endpoint for BHOOMI V2:
    Farmer Audio In -> STT (Sarvam saaras) -> Language Normalization ->
    BHOOMI Agent Orchestrator (Same reasoning pipeline as text chat) ->
    Deterministic Domain Tools -> SafetyEngine -> TTS (Sarvam bulbul) -> Structured Response
    """
    audio_bytes = await read_audio_payload(file)
    logger.info(f"[VOICE_LOOP] [STAGE 1: RECORDING_RECEIVED] size={len(audio_bytes)} bytes, filename={file.filename}, content_type={file.content_type}")
    safe_print(f"[VOICE_LOOP] [STAGE 1: RECORDING_RECEIVED] size={len(audio_bytes)} bytes, filename={file.filename}", flush=True)
    provider = get_voice_provider()
    preferred_lang = language or farmer.preferred_language or "en"
    
    # 1. Speech to Text (Sarvam STT)
    try:
        trans_res = await provider.transcribe(audio_bytes=audio_bytes, language_code=preferred_lang)
    except VoiceProcessingException as exc:
        err_msg = exc.detail.get("error", {}).get("message", str(exc)) if isinstance(exc.detail, dict) else str(exc)
        logger.warning(f"[VOICE_LOOP] [STAGE 2: STT_FAILED] error={err_msg}")
        safe_print(f"[VOICE_LOOP] [STAGE 2: STT_FAILED] error={err_msg}", flush=True)
        raise exc

    user_text = trans_res.text.strip()
    active_lang = trans_res.language_code or preferred_lang
    logger.info(f"[VOICE_LOOP] [STAGE 2: STT_SUCCESS] transcript='{user_text}', detected_lang='{active_lang}', confidence={trans_res.confidence}")
    safe_print(f"[VOICE_LOOP] [STAGE 2: STT_SUCCESS] transcript='{user_text}', detected_lang='{active_lang}'", flush=True)

    # 2. Handle Empty or Unintelligible Transcript Gracefully
    if not user_text:
        fallback_msg = FALLBACK_PROMPTS.get(active_lang, FALLBACK_PROMPTS["en"])
        b64_audio = ""
        try:
            tts_res = await provider.synthesize(text=fallback_msg, language_code=active_lang)
            b64_audio = base64.b64encode(tts_res.audio_bytes).decode("utf-8")
        except Exception as exc:
            logger.warning(f"[VOICE_LOOP] Fallback TTS synthesis failed: {exc}")
        return VoiceInteractResponse(
            user_transcription="",
            detected_language=active_lang,
            assistant_text=fallback_msg,
            assistant_audio_base64=b64_audio,
            visual_cards=[],
            session_id=session_id or "session_fallback",
            message_id="msg_clarification",
            voice_state="RESPONDING"
        )

    # 3. Get / Create Chat Session
    chat_repo = ChatRepository(db)
    session = await chat_repo.get_or_create_session(
        farmer.id,
        session_id=session_id if session_id else None,
        language=active_lang
    )

    # 4. Save User Voice Message to History
    try:
        await chat_repo.save_message(
            session_id=session.id,
            sender="user",
            content=user_text,
            input_mode="voice",
        )
    except Exception as e:
        logger.warning(f"Error saving user voice message: {e}")

    # 5. Execute Core Decision Intelligence Loop via BhoomiAgentOrchestrator
    logger.info(f"[VOICE_LOOP] [STAGE 3: ORCHESTRATOR] user_text='{user_text}', farmer_id='{farmer.id}'")
    orch_result = await BhoomiAgentOrchestrator.process_turn(
        db=db,
        farmer_id=farmer.id,
        session_id=session.id,
        user_text=user_text,
        input_mode="voice",
        language=active_lang
    )
    logger.info(f"[VOICE_LOOP] [STAGE 4: RESPONSE_GENERATED] response_text='{orch_result.response_text}'")
    safe_print(f"[VOICE_LOOP] [STAGE 4: RESPONSE_GENERATED] response_text='{orch_result.response_text}'", flush=True)

    # 6. Text to Speech Synthesis (Sarvam TTS)
    try:
        tts_res = await provider.synthesize(
            text=orch_result.response_text,
            language_code=active_lang,
        )
        b64_audio = base64.b64encode(tts_res.audio_bytes).decode("utf-8")
        logger.info(f"[VOICE_LOOP] [STAGE 5: TTS_SUCCESS] audio_bytes={len(tts_res.audio_bytes)}, b64_len={len(b64_audio)}")
        safe_print(f"[VOICE_LOOP] [STAGE 5: TTS_SUCCESS] audio_bytes={len(tts_res.audio_bytes)}", flush=True)
    except Exception as exc:
        logger.warning(f"[VOICE_LOOP] [STAGE 5: TTS_FAILED] error={str(exc)}")
        safe_print(f"[VOICE_LOOP] [STAGE 5: TTS_FAILED] error={str(exc)}", flush=True)
        b64_audio = ""

    # 7. Save Assistant Message with Visual Cards
    msg_id = "msg_asst"
    try:
        asst_msg = await chat_repo.save_message(
            session_id=session.id,
            sender="assistant",
            content=orch_result.response_text,
            input_mode="voice",
            structured_payload={"visual_cards": orch_result.visual_cards} if orch_result.visual_cards else None
        )
        msg_id = asst_msg.id
    except Exception as e:
        logger.warning(f"Error saving assistant voice message: {e}")

    return VoiceInteractResponse(
        user_transcription=user_text,
        detected_language=active_lang,
        assistant_text=orch_result.response_text,
        assistant_audio_base64=b64_audio,
        visual_cards=orch_result.visual_cards,
        session_id=session.id,
        message_id=msg_id,
        voice_state="RESPONDING"
    )


@router.post("/task-action", response_model=VoiceTaskActionResponse)
async def voice_task_action(
    req: VoiceTaskActionRequest,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Canonical Voice & Typing Task Action Endpoint:
    Enables voice/text based status updates, postponement, skip, and confirmations.
    Voice and typing share the exact same decision and state-machine pipeline.
    """
    farmer_id = getattr(farmer, "id", None) or req.farmer_id or "farmer_demo_1"
    session_id = req.conversation_id or "session_demo_1"
    target_lang = req.language or getattr(farmer, "preferred_language", "en") or "en"

    user_text = req.text or ""
    if req.audio:
        # Transcribe audio if provided
        provider = get_voice_provider()
        try:
            audio_bytes = base64.b64decode(req.audio)
            trans_res = await provider.transcribe(audio_bytes=audio_bytes, language_code=target_lang)
            user_text = trans_res.text
            target_lang = trans_res.language_code or target_lang
        except Exception as exc:
            logger.warning(f"Failed to transcribe task-action audio: {exc}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to process voice audio.")

    if not user_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No voice transcript or text provided.")

    # Process turn through BhoomiAgentOrchestrator
    input_mode = "voice" if req.audio else "text"
    orch_result = await BhoomiAgentOrchestrator.process_turn(
        db=db,
        farmer_id=farmer_id,
        session_id=session_id,
        user_text=user_text,
        input_mode=input_mode,
        language=target_lang
    )

    # Inspect if a pending confirmation session was opened
    pending_sess = ConfirmationStateMachine.get_session(session_id, farmer_id)
    requires_conf = False
    task_id = None
    action = "INFO"
    stat = "PROCESSED"

    if pending_sess and pending_sess.state in [
        ConfirmationState.AWAITING_CONFIRMATION,
        ConfirmationState.AWAITING_TASK_SELECTION,
        ConfirmationState.AWAITING_DELAY
    ]:
        requires_conf = True
        task_id = pending_sess.selected_task_id
        action = pending_sess.pending_action
        stat = pending_sess.state.value
    else:
        # Parse intent to populate response metadata
        parsed_intent = IntentNormalizationService.parse_intent(user_text, language=target_lang)
        action = parsed_intent.intent_type.value
        task_id = parsed_intent.target_task_id
        stat = "SUCCESS"

    return VoiceTaskActionResponse(
        intent=action,
        task_id=task_id,
        action=action,
        status=stat,
        requires_confirmation=requires_conf,
        response_text=orch_result.response_text,
        language=target_lang,
        trace_id=orch_result.trace_id or ""
    )

class WebTTSRequest(BaseModel):
    text: str
    language_code: Optional[str] = "en"
    slow_speed: Optional[bool] = False

@router.post("/tts")
async def web_tts(
    req: WebTTSRequest,
    farmer: Optional[FarmerProfile] = Depends(get_current_farmer_profile_optional)
):
    provider = get_voice_provider()
    lang = req.language_code or (farmer.preferred_language if farmer else "en")
    try:
        res = await provider.synthesize(text=req.text, language_code=lang)
        b64_audio = base64.b64encode(res.audio_bytes).decode("utf-8")
        mime = res.content_type or "audio/mp3"
        return {
            "status": "success",
            "audio_base64": f"data:{mime};base64,{b64_audio}"
        }
    except VoiceProcessingException as exc:
        msg = exc.detail.get("error", {}).get("message", str(exc)) if isinstance(exc.detail, dict) else str(exc)
        logger.warning(f"Web TTS failed ({exc.status_code}): {msg}")
        raise HTTPException(status_code=exc.status_code, detail=msg)
    except Exception as exc:
        logger.warning(f"Web TTS failed: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

@router.post("/stt")
async def web_stt(
    file: UploadFile = File(...),
    language_code: Optional[str] = Form(default="te"),
    farmer: FarmerProfile = Depends(get_current_farmer_profile)
):
    audio_bytes = await read_audio_payload(file)
    provider = get_voice_provider()
    lang = language_code or farmer.preferred_language or "te"
    try:
        res = await provider.transcribe(audio_bytes=audio_bytes, language_code=lang)
        return {
            "status": "success",
            "transcript": res.text,
            "language_code": res.language_code,
            "confidence": res.confidence
        }
    except VoiceProcessingException as exc:
        msg = exc.detail.get("error", {}).get("message", str(exc)) if isinstance(exc.detail, dict) else str(exc)
        logger.warning(f"Web STT failed ({exc.status_code}): {msg}")
        raise HTTPException(status_code=exc.status_code, detail=msg)
    except Exception as exc:
        logger.warning(f"Web STT failed: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


