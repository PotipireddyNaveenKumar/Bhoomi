import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.chat import ChatSession, ChatMessage
from app.core.datetime_utils import utc_now_naive

class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(self, farmer_id: str, session_id: Optional[str] = None, language: str = "en") -> ChatSession:
        if session_id:
            result = await self.db.execute(
                select(ChatSession).options(selectinload(ChatSession.messages)).where(
                    ChatSession.id == session_id,
                    ChatSession.farmer_id == farmer_id
                )
            )
            session = result.scalars().first()
            if session:
                return session

        now_naive = utc_now_naive()
        new_session = ChatSession(
            id=session_id if session_id else str(uuid.uuid4()),
            farmer_id=farmer_id,
            title="Farm Advisory Session",
            language=language,
            created_at=now_naive,
            updated_at=now_naive
        )
        self.db.add(new_session)
        await self.db.commit()
        await self.db.refresh(new_session)
        # load messages
        result = await self.db.execute(
            select(ChatSession).options(selectinload(ChatSession.messages)).where(ChatSession.id == new_session.id)
        )
        return result.scalars().first()

    async def get_farmer_sessions(self, farmer_id: str) -> List[ChatSession]:
        result = await self.db.execute(
            select(ChatSession).options(selectinload(ChatSession.messages)).where(
                ChatSession.farmer_id == farmer_id
            ).order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def save_message(
        self,
        session_id: str,
        sender: str,
        content: str,
        input_mode: str = "text",
        audio_url: Optional[str] = None,
        image_url: Optional[str] = None,
        structured_payload: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        # Ensure structured_payload and metadata are fully JSON serializable (handling datetime, etc.)
        sanitized_payload = None
        if structured_payload is not None:
            import json
            sanitized_payload = json.loads(json.dumps(structured_payload, default=str))

        sanitized_metadata = None
        if metadata is not None:
            import json
            sanitized_metadata = json.loads(json.dumps(metadata, default=str))

        now_naive = utc_now_naive()
        msg = ChatMessage(
            session_id=session_id,
            sender=sender,
            input_mode=input_mode,
            content=content,
            audio_url=audio_url,
            image_url=image_url,
            structured_payload=sanitized_payload,
            metadata_json=sanitized_metadata,
            created_at=now_naive,
        )
        self.db.add(msg)

        # Update session updated_at timestamp in naive UTC
        result = await self.db.execute(select(ChatSession).where(ChatSession.id == session_id))
        session = result.scalars().first()
        if session:
            session.updated_at = now_naive

        await self.db.commit()
        await self.db.refresh(msg)
        return msg
