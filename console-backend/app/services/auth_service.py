"""Registration, verified Google sign-in, and atomic refresh-token rotation."""

import asyncio
import hashlib
import uuid

from google.auth.exceptions import GoogleAuthError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.exceptions import ConflictError, ServiceUnavailableError, UnauthorizedError
from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.schemas.auth import TokenResponse
from app.services.user_service import UserService


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserService(db)

    async def register(self, *, email: str, password: str, full_name: str | None) -> TokenResponse:
        existing = await self.users.get_by_email(email)
        if existing:
            raise ConflictError("An account with this email already exists")

        user = await self.users.create(
            email=email,
            hashed_password=await run_in_threadpool(hash_password, password),
            full_name=full_name,
        )
        return await self._issue_tokens(user)

    async def login(self, *, email: str, password: str) -> TokenResponse:
        user = await self.users.get_by_email(email)
        if (
            not user
            or not user.hashed_password
            or not await run_in_threadpool(verify_password, password, user.hashed_password)
        ):
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated")

        return await self._issue_tokens(user)

    async def login_with_google(self, id_token: str) -> TokenResponse:
        if not settings.GOOGLE_OAUTH_CLIENT_ID:
            raise ServiceUnavailableError("Google login is not configured")
        from google.auth.transport.requests import Request

        class BoundedRequest(Request):
            def __call__(self, *args, **kwargs):
                kwargs["timeout"] = 10
                return super().__call__(*args, **kwargs)

        from google.oauth2.id_token import verify_oauth2_token

        try:
            claims = await asyncio.to_thread(
                verify_oauth2_token, id_token, BoundedRequest(), settings.GOOGLE_OAUTH_CLIENT_ID
            )
        except (ValueError, GoogleAuthError) as exc:
            raise UnauthorizedError("Invalid Google ID token") from exc
        if not claims.get("email_verified") or not claims.get("email") or not claims.get("sub"):
            raise UnauthorizedError("Google account must have a verified email")
        user = await self.db.scalar(
            select(User).where(User.oauth_provider == "google", User.oauth_sub == claims["sub"])
        )
        if user is None:
            user = await self.users.get_by_email(claims["email"])
        if user:
            # Email alone is not an account-linking credential.
            if user.oauth_provider != "google" or user.oauth_sub != claims["sub"]:
                raise ConflictError("Sign in with the existing account's login method")
            if not user.is_active:
                raise UnauthorizedError("This account has been deactivated")
        else:
            user = await self.users.create(
                email=claims["email"], hashed_password=None, full_name=claims.get("name")
            )
            user.oauth_provider = "google"
            user.oauth_sub = claims["sub"]
            user.is_verified = True
        return await self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != TokenType.REFRESH.value:
            raise UnauthorizedError("Invalid or expired refresh token")

        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == hashlib.sha256(refresh_token.encode()).hexdigest(),
                RefreshToken.revoked.is_(False),
            )
        )
        stored = result.scalar_one_or_none()
        if not stored:
            raise UnauthorizedError("Refresh token has been revoked")

        user = await self.users.get_by_id(payload["sub"])
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")

        result = await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.id == stored.id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise UnauthorizedError("Refresh token has been revoked")
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == hashlib.sha256(refresh_token.encode()).hexdigest()
            )
        )
        stored = result.scalar_one_or_none()
        if stored:
            stored.revoked = True
            await self.db.commit()

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        self.db.add(
            RefreshToken(
                id=uuid.uuid4(),
                user_id=user.id,
                token=hashlib.sha256(refresh_token.encode()).hexdigest(),
            )
        )
        await self.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )
