from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: str
    farmer_id: str
    farm_id: str
    task_id: str
    event_id: str
    event_key: str
    notification_type: str
    title: str
    message: str
    locale: str = "en"
    priority: str = "MEDIUM"
    created_at: datetime
    read_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    meta_payload: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationAcknowledgeResponse(BaseModel):
    success: bool
    notification: NotificationResponse
