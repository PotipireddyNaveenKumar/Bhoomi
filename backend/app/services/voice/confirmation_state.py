import time
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ConfirmationState(str, Enum):
    NO_CONFIRMATION = "NO_CONFIRMATION"
    AWAITING_TASK_SELECTION = "AWAITING_TASK_SELECTION"
    AWAITING_DATE = "AWAITING_DATE"
    AWAITING_DELAY = "AWAITING_DELAY"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PendingActionSession(BaseModel):
    session_id: str
    farmer_id: str
    state: ConfirmationState = ConfirmationState.NO_CONFIRMATION
    pending_action: str  # COMPLETE, POSTPONE, SKIP
    candidate_task_ids: List[str] = Field(default_factory=list)
    selected_task_id: Optional[str] = None
    target_crop: Optional[str] = None
    target_task_type: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    prompt_message: str = ""
    created_at_epoch: float = Field(default_factory=time.time)
    timeout_seconds: float = 300.0  # 5-minute confirmation TTL


class ConfirmationStateMachine:
    """
    Session-level Confirmation State Machine.
    Ensures consequential actions (e.g. skipping irrigation when moisture is deficient,
    or disambiguating between multiple active tasks) require deterministic farmer confirmation.
    Safely times out abandoned confirmations.
    """
    _sessions: Dict[str, PendingActionSession] = {}

    @classmethod
    def get_session(cls, session_id: str, farmer_id: Optional[str] = None) -> Optional[PendingActionSession]:
        sess = cls._sessions.get(session_id)
        if not sess and farmer_id:
            sess = cls._sessions.get(farmer_id)
        if not sess:
            return None
        # Check timeout
        if time.time() - sess.created_at_epoch > sess.timeout_seconds:
            cls.clear_session(session_id, farmer_id)
            return None
        return sess

    @classmethod
    def start_confirmation(
        cls,
        session_id: str,
        farmer_id: str,
        state: ConfirmationState,
        action: str,
        prompt_message: str,
        candidate_task_ids: Optional[List[str]] = None,
        selected_task_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> PendingActionSession:
        sess = PendingActionSession(
            session_id=session_id,
            farmer_id=farmer_id,
            state=state,
            pending_action=action,
            prompt_message=prompt_message,
            candidate_task_ids=candidate_task_ids or [],
            selected_task_id=selected_task_id,
            parameters=parameters or {},
            created_at_epoch=time.time()
        )
        cls._sessions[session_id] = sess
        if farmer_id:
            cls._sessions[farmer_id] = sess
        return sess

    @classmethod
    def clear_session(cls, session_id: str, farmer_id: Optional[str] = None):
        if session_id in cls._sessions:
            del cls._sessions[session_id]
        if farmer_id and farmer_id in cls._sessions:
            del cls._sessions[farmer_id]

