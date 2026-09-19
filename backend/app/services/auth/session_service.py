import secrets
import hashlib
from datetime import timedelta
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.datetime_utils import utc_now_naive
from app.core.logging import logger
from app.core.security import create_access_token
from app.models.auth_session import AuthSession
from app.models.user import User

ACCESS_TOKEN_LIFETIME_MINUTES = 60  # 1 hour
REFRESH_TOKEN_LIFETIME_DAYS = 30    # 30 days

class SessionService:
    """
    Manages authenticated sessions, JWT access tokens, and database-backed refresh tokens.
    Never stores plaintext refresh tokens in the database.
    """

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        """Computes SHA-256 hash of the raw refresh token for safe storage."""
        return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()

    @classmethod
    async def create_session(
        cls,
        db: AsyncSession,
        user_id: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Creates an access token and a database-backed refresh token session.
        Returns:
            Tuple[access_token, raw_refresh_token]
        """
        now = utc_now_naive()
        access_token = create_access_token(
            subject=user_id,
            expires_delta=timedelta(minutes=ACCESS_TOKEN_LIFETIME_MINUTES)
        )

        raw_refresh_token = secrets.token_urlsafe(48)
        refresh_hash = cls.hash_refresh_token(raw_refresh_token)

        session = AuthSession(
            user_id=user_id,
            refresh_token_hash=refresh_hash,
            created_at=now,
            expires_at=now + timedelta(days=getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", REFRESH_TOKEN_LIFETIME_DAYS)),
            revoked_at=None,
            last_used_at=now,
            device_info=device_info,
            ip_address=ip_address
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        logger.info(f"Created new authenticated session for user {user_id} (session_id={session.id}).")
        return access_token, raw_refresh_token

    @classmethod
    async def refresh_session(
        cls,
        db: AsyncSession,
        raw_refresh_token: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Validates a refresh token and issues a new access token and rotated refresh token.
        Revokes old session and returns (new_access_token, new_refresh_token).
        """
        if not raw_refresh_token or not isinstance(raw_refresh_token, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token cannot be empty."
            )

        token_hash = cls.hash_refresh_token(raw_refresh_token)
        now = utc_now_naive()

        res = await db.execute(
            select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
        )
        session = res.scalars().first()

        if not session:
            logger.warning("Refresh attempt with non-existent token hash.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token."
            )

        if session.revoked_at is not None:
            logger.warning(f"Refresh attempt on revoked session {session.id} for user {session.user_id}.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked. Please log in again."
            )

        if session.expires_at <= now:
            logger.warning(f"Refresh attempt on expired session {session.id} for user {session.user_id}.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired. Please log in again."
            )

        # Check user status
        res_user = await db.execute(select(User).where(User.id == session.user_id))
        user = res_user.scalars().first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive or disabled."
            )

        # Revoke the old refresh token (Token Rotation Security)
        session.revoked_at = now
        session.last_used_at = now

        # Create fresh session
        new_access, new_refresh = await cls.create_session(
            db=db,
            user_id=user.id,
            device_info=device_info or session.device_info,
            ip_address=ip_address or session.ip_address
        )

        return new_access, new_refresh

    @classmethod
    async def revoke_session(
        cls,
        db: AsyncSession,
        raw_refresh_token: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Revokes an authenticated session.
        If raw_refresh_token is provided, revokes that specific session.
        If only user_id is provided, revokes all active sessions for that user.
        """
        now = utc_now_naive()
        if raw_refresh_token:
            token_hash = cls.hash_refresh_token(raw_refresh_token)
            await db.execute(
                update(AuthSession)
                .where(AuthSession.refresh_token_hash == token_hash, AuthSession.revoked_at.is_(None))
                .values(revoked_at=now)
            )
            await db.commit()
            logger.info("Revoked specific auth session.")
            return True
        elif user_id:
            await db.execute(
                update(AuthSession)
                .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
                .values(revoked_at=now)
            )
            await db.commit()
            logger.info(f"Revoked all auth sessions for user {user_id}.")
            return True
        return False
