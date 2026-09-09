from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.repositories.chat_repo import ChatRepository
from app.agents.orchestrator import BhoomiAgentOrchestrator
from app.schemas.chat import (
    ChatMessageCreate, ChatMessageResponse, ChatSessionResponse, VisualCard
)

router = APIRouter(prefix="/chat", tags=["Chat & Conversations"])

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = ChatRepository(db)
    sessions = await repo.get_farmer_sessions(farmer.id)
    return sessions

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: str,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = ChatRepository(db)
    session = await repo.get_or_create_session(farmer.id, session_id=session_id)
    return session

@router.post("", response_model=ChatMessageResponse)
async def send_message(
    msg_in: ChatMessageCreate,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db)
):
    repo = ChatRepository(db)
    session = await repo.get_or_create_session(farmer.id, msg_in.session_id, language=msg_in.language or farmer.preferred_language)

    # 1. Save user message
    user_msg = await repo.save_message(
        session_id=session.id,
        sender="user",
        content=msg_in.content,
        input_mode=msg_in.input_mode,
        audio_url=msg_in.audio_url,
        image_url=msg_in.image_url,
    )

    # 2. Run BHOOMI AI Agent Orchestration Loop
    result = await BhoomiAgentOrchestrator.process_turn(
        db=db,
        farmer_id=farmer.id,
        session_id=session.id,
        user_text=msg_in.content,
        input_mode=msg_in.input_mode,
        language=msg_in.language or farmer.preferred_language
    )

    # 3. Save Assistant Message with Visual Cards
    assistant_msg = await repo.save_message(
        session_id=session.id,
        sender="assistant",
        content=result.response_text,
        input_mode="text",
        structured_payload={"visual_cards": result.visual_cards} if result.visual_cards else None,
    )

    # Convert visual cards for response
    cards = [
        VisualCard(
            card_type=c.get("card_type", "generic_card"),
            title=c.get("title", "Farm Advisory"),
            subtitle=c.get("subtitle"),
            data=c.get("data", {})
        ) for c in result.visual_cards
    ]

    # Extract sources from visual cards
    sources = []
    for c in result.visual_cards:
        if "citations" in c.get("data", {}):
            sources.extend(c["data"]["citations"])

    return ChatMessageResponse(
        id=assistant_msg.id,
        session_id=session.id,
        sender="assistant",
        input_mode="text",
        content=result.response_text,
        visual_cards=cards,
        structured_payload=assistant_msg.structured_payload,
        voice_state=result.voice_state,
        intent=getattr(result, "intent", "GENERAL_AGRICULTURE"),
        trace_id=getattr(result, "trace_id", None),
        sources=sources,
        actions=[],
        created_at=assistant_msg.created_at
    )
