import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, ForeignKey, JSON, Enum
import enum
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.core.datetime_utils import NaiveUTCDateTime, utc_now_naive

class MessageSender(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class InputMode(str, enum.Enum):
    VOICE = "voice"
    TEXT = "text"
    IMAGE = "image"

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    farmer_id = Column(String(36), ForeignKey("farmer_profiles.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), default="New Conversation", nullable=False)
    language = Column(String(10), default="en", nullable=False)
    created_at = Column(NaiveUTCDateTime, default=utc_now_naive)
    updated_at = Column(NaiveUTCDateTime, default=utc_now_naive, onupdate=utc_now_naive)

    farmer = relationship("FarmerProfile", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(20), default=MessageSender.USER.value, nullable=False)
    input_mode = Column(String(20), default=InputMode.VOICE.value, nullable=False)
    content = Column(Text, nullable=False)
    audio_url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    structured_payload = Column(JSON, nullable=True)  # Visual card payload: { "card_type": "weather_card", "data": {...} }
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(NaiveUTCDateTime, default=utc_now_naive)

    session = relationship("ChatSession", back_populates="messages")
