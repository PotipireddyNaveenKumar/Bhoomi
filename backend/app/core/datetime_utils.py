"""
BHOOMI V2 Canonical Database Datetime Utility

Canonical Policy:
Database timestamps are stored as offset-naive UTC because the existing PostgreSQL
schema uses TIMESTAMP WITHOUT TIME ZONE (asyncpg strictly disallows offset-aware
datetimes for TIMESTAMP WITHOUT TIME ZONE columns, raising DataError: can't subtract
offset-naive and offset-aware datetimes).

All database datetime fields in SQLAlchemy models use NaiveUTCDateTime and default to
utc_now_naive(). Any aware datetime passed into a model attribute is automatically
converted to UTC and stripped of tzinfo before bind-parameter execution.
"""
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import TypeDecorator, DateTime


def utc_now_naive() -> datetime:
    """
    Returns the current UTC time as an offset-naive datetime.
    
    Database timestamps are stored as naive UTC because the existing PostgreSQL
    schema uses TIMESTAMP WITHOUT TIME ZONE.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_utc_naive(dt: Optional[Any]) -> Optional[datetime]:
    """
    Ensures that a datetime object is an offset-naive datetime representing UTC.
    If dt is timezone-aware, converts to UTC and drops tzinfo.
    If dt is already naive, assumes it represents UTC and returns it as-is.
    If dt is an ISO format string, attempts parsing.
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return None
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    return dt


class NaiveUTCDateTime(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that guarantees all datetimes bound to
    TIMESTAMP WITHOUT TIME ZONE columns are converted to offset-naive UTC datetimes
    before being passed to asyncpg/PostgreSQL.
    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect: Any) -> Optional[datetime]:
        if value is not None:
            return ensure_utc_naive(value)
        return None

    def process_result_value(self, value: Optional[Any], dialect: Any) -> Optional[datetime]:
        return value
