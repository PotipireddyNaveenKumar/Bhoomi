import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.session import get_db
from app.api.deps import get_current_farmer_profile
from app.models.farmer import FarmerProfile
from app.models.notification import FarmerNotification
from app.models.task_event import FarmTaskEvent
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationAcknowledgeResponse
)
from app.core.datetime_utils import utc_now_naive

logger = logging.getLogger("bhoomi.api.notifications")

router = APIRouter(prefix="/notifications", tags=["Farmer Notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves farmer-facing notifications for the authenticated farmer.
    Tenant-isolated: strictly filters by authenticated farmer.id.
    """
    # Count unread notifications
    unread_stmt = select(func.count(FarmerNotification.id)).where(
        FarmerNotification.farmer_id == farmer.id,
        FarmerNotification.read_at.is_(None)
    )
    unread_count = (await db.execute(unread_stmt)).scalar_one() or 0

    # Build query for notifications
    query = select(FarmerNotification).where(FarmerNotification.farmer_id == farmer.id)
    if unread_only:
        query = query.where(FarmerNotification.read_at.is_(None))

    # Total matching
    count_stmt = select(func.count(FarmerNotification.id)).where(FarmerNotification.farmer_id == farmer.id)
    if unread_only:
        count_stmt = count_stmt.where(FarmerNotification.read_at.is_(None))
    total = (await db.execute(count_stmt)).scalar_one() or 0

    query = query.order_by(FarmerNotification.created_at.desc()).offset(offset).limit(limit)
    res = await db.execute(query)
    items = list(res.scalars().all())

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        total=total,
        unread_count=unread_count
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns unread notification count for the authenticated farmer.
    """
    stmt = select(func.count(FarmerNotification.id)).where(
        FarmerNotification.farmer_id == farmer.id,
        FarmerNotification.read_at.is_(None)
    )
    unread_count = (await db.execute(stmt)).scalar_one() or 0
    return UnreadCountResponse(unread_count=unread_count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Marks a notification as read for the authenticated farmer.
    Enforces strict tenant isolation.
    """
    # Check if notification exists for current farmer
    stmt = select(FarmerNotification).where(FarmerNotification.id == notification_id)
    notif = (await db.execute(stmt)).scalar_one_or_none()

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found."
        )

    if notif.farmer_id != farmer.id:
        logger.warning(
            f"SECURITY_ALERT cross-tenant read attempt: farmer={farmer.id} tried accessing notification={notification_id} owned by farmer={notif.farmer_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this notification."
        )

    if not notif.read_at:
        notif.read_at = utc_now_naive()
        await db.commit()
        await db.refresh(notif)

    return NotificationResponse.model_validate(notif)


@router.post("/{notification_id}/acknowledge", response_model=NotificationAcknowledgeResponse)
async def acknowledge_notification(
    notification_id: str,
    farmer: FarmerProfile = Depends(get_current_farmer_profile),
    db: AsyncSession = Depends(get_db),
):
    """
    Acknowledges a notification and syncs acknowledgement state with source FarmTaskEvent.
    Enforces strict tenant isolation.
    """
    stmt = select(FarmerNotification).where(FarmerNotification.id == notification_id)
    notif = (await db.execute(stmt)).scalar_one_or_none()

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found."
        )

    if notif.farmer_id != farmer.id:
        logger.warning(
            f"SECURITY_ALERT cross-tenant acknowledge attempt: farmer={farmer.id} tried acknowledging notification={notification_id} owned by farmer={notif.farmer_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this notification."
        )

    now = utc_now_naive()
    if not notif.acknowledged_at:
        notif.acknowledged_at = now
    if not notif.read_at:
        notif.read_at = now

    # Also update source event if present
    if notif.event_id:
        event_stmt = select(FarmTaskEvent).where(FarmTaskEvent.id == notif.event_id)
        source_event = (await db.execute(event_stmt)).scalar_one_or_none()
        if source_event and not source_event.acknowledged_at:
            source_event.acknowledged_at = now

    await db.commit()
    await db.refresh(notif)

    return NotificationAcknowledgeResponse(
        success=True,
        notification=NotificationResponse.model_validate(notif)
    )
