import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class DialogueSession(BaseModel):
    """
    Multi-Turn Conversational Memory and Dialogue State for BHOOMI V2.
    Tracks active topic, pending questions, slot values, last referenced tasks/weather/market,
    and turn history so BHOOMI behaves as a continuous conversational farm manager.
    """
    session_id: str
    farmer_id: str
    language: str = "en"
    active_topic: Optional[str] = None  # CROP_PLANNING, IRRIGATION, WEATHER, TASKS, MARKET, PEST_DISEASE, FERTILIZER
    pending_slot: Optional[str] = None  # SOIL_TYPE, IRRIGATION_AVAILABILITY, CONFIRM_CROP_RECOMMENDATION, etc.
    collected_slots: Dict[str, Any] = Field(default_factory=dict)  # soil_type, irrigation_water, crop, area
    last_discussed_task: Optional[Dict[str, Any]] = None  # Task ID, title, type, crop
    last_weather_context: Optional[Dict[str, Any]] = None  # temp, condition, rain probability
    last_market_context: Optional[Dict[str, Any]] = None
    last_crop_recommendation: Optional[Dict[str, Any]] = None
    recent_turns: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FarmerDialogueManager:
    """
    Singleton Manager for Stateful Farmer Dialogue Sessions.
    Enforces conversation continuity across voice and text turns.
    """
    _sessions: Dict[str, DialogueSession] = {}

    @classmethod
    def _make_key(cls, session_id: str, farmer_id: str) -> str:
        return f"{session_id or 'default'}:{farmer_id or 'default'}"

    @classmethod
    def get_or_create_session(cls, session_id: str, farmer_id: str, language: str = "en") -> DialogueSession:
        key = cls._make_key(session_id, farmer_id)
        if key not in cls._sessions:
            cls._sessions[key] = DialogueSession(
                session_id=session_id or "session_default",
                farmer_id=farmer_id or "farmer_default",
                language=language or "en"
            )
        session = cls._sessions[key]
        if language and language != "en" and session.language == "en":
            session.language = language
        return session

    @classmethod
    def get_session(cls, session_id: str, farmer_id: str) -> Optional[DialogueSession]:
        key = cls._make_key(session_id, farmer_id)
        return cls._sessions.get(key)

    @classmethod
    def set_active_topic(
        cls,
        session_id: str,
        farmer_id: str,
        topic: Optional[str],
        pending_slot: Optional[str] = None
    ) -> DialogueSession:
        session = cls.get_or_create_session(session_id, farmer_id)
        session.active_topic = topic
        session.pending_slot = pending_slot
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return session

    @classmethod
    def update_slot(
        cls,
        session_id: str,
        farmer_id: str,
        slot_name: str,
        slot_value: Any
    ) -> DialogueSession:
        session = cls.get_or_create_session(session_id, farmer_id)
        session.collected_slots[slot_name] = slot_value
        session.updated_at = datetime.now(timezone.utc).isoformat()
        return session

    @classmethod
    def set_last_discussed_task(
        cls,
        session_id: str,
        farmer_id: str,
        task: Any
    ) -> None:
        session = cls.get_or_create_session(session_id, farmer_id)
        if isinstance(task, dict):
            session.last_discussed_task = task
        elif hasattr(task, "model_dump"):
            session.last_discussed_task = task.model_dump()
        elif hasattr(task, "__dict__"):
            session.last_discussed_task = {
                "task_id": getattr(task, "task_id", None),
                "title": getattr(task, "title", "Scheduled Farm Task"),
                "task_type": getattr(task, "task_type", None),
                "crop": getattr(task, "crop", "Chilli"),
                "status": getattr(task, "status", "DUE"),
                "due_at": getattr(task, "due_at", None),
            }
        session.updated_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def get_last_discussed_task(cls, session_id: str, farmer_id: str) -> Optional[Dict[str, Any]]:
        session = cls.get_session(session_id, farmer_id)
        return session.last_discussed_task if session else None

    @classmethod
    def resolve_pronoun_task(
        cls,
        session_id: str,
        farmer_id: str,
        candidate_tasks: List[Any]
    ) -> Optional[Any]:
        """
        Resolves ambiguous pronoun references (e.g. 'postpone it', 'skip it', 'finished it')
        to the task discussed in the immediately preceding conversation turn.
        """
        session = cls.get_session(session_id, farmer_id)
        if not session or not session.last_discussed_task:
            return None

        target_id = session.last_discussed_task.get("task_id")
        target_title = session.last_discussed_task.get("title")
        target_type = session.last_discussed_task.get("task_type")

        # Match by task_id first
        if target_id:
            for t in candidate_tasks:
                if getattr(t, "task_id", None) == target_id:
                    return t

        # Match by title or task_type
        for t in candidate_tasks:
            t_title = getattr(t, "title", "")
            t_type = getattr(t, "task_type", None)
            if target_title and t_title == target_title:
                return t
            if target_type and t_type == target_type:
                return t

        return None

    @classmethod
    def record_turn(
        cls,
        session_id: str,
        farmer_id: str,
        user_text: str,
        response_text: str,
        intent: str = "UNKNOWN",
        cards: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        session = cls.get_or_create_session(session_id, farmer_id)
        turn_entry = {
            "turn_index": len(session.recent_turns) + 1,
            "user_text": user_text,
            "response_text": response_text,
            "intent": intent,
            "card_count": len(cards) if cards else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        session.recent_turns.append(turn_entry)
        # Keep recent 15 turns
        if len(session.recent_turns) > 15:
            session.recent_turns = session.recent_turns[-15:]
        session.updated_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def clear_session(cls, session_id: str, farmer_id: str) -> None:
        key = cls._make_key(session_id, farmer_id)
        if key in cls._sessions:
            del cls._sessions[key]
