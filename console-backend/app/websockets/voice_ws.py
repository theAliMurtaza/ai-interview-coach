"""WebSocket authentication shared with the voice route.

Browsers send an access token as their first JSON message, never in a URL.
"""

import asyncio

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import TokenType, decode_token
from app.services.user_service import UserService


async def authenticate_socket(websocket: WebSocket, db: AsyncSession):
    try:
        message = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        token = message.get("access_token") if isinstance(message, dict) else None
        payload = decode_token(token) if isinstance(token, str) and len(token) <= 4096 else None
        if not payload or payload.get("type") != TokenType.ACCESS:
            raise UnauthorizedError("Invalid access token")
        user = await UserService(db).get_by_id(payload["sub"])
        if not user or not user.is_active:
            raise UnauthorizedError("User is inactive")
        return user, payload["exp"]
    except (ValueError, TimeoutError) as exc:
        raise UnauthorizedError("Authentication required") from exc
