"""Authenticated voice socket; send complete audio clips, one binary frame per clip."""

import asyncio
import time
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.core.exceptions import AppError, ConflictError, ForbiddenError
from app.core.rate_limit import check_rate_limit
from app.models.interview import InterviewStatus
from app.services.answer_service import AnswerService
from app.services.voice_service import VoiceService
from app.websockets.voice_ws import authenticate_socket

router = APIRouter(prefix="/voice", tags=["voice"])


@router.websocket("/ws/{question_id}")
async def voice_stream(
    websocket: WebSocket, question_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.BACKEND_CORS_ORIGINS:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        host = websocket.client.host if websocket.client else "unknown"
        await check_rate_limit(f"voice-connect:{host}", settings.AUTH_RATE_LIMIT_PER_MINUTE)
        user, expires_at = await authenticate_socket(websocket, db)
        user_id = user.id
        question = await AnswerService(db).get_question_or_404(question_id)
        if question.interview.user_id != user_id:
            raise ForbiddenError("Question belongs to another user")
        if question.interview.status != InterviewStatus.IN_PROGRESS:
            raise ConflictError("Interview is no longer in progress")
        question_text = question.text
        await db.rollback()  # Do not hold a database transaction during an open socket.
        await websocket.send_json({"authenticated": True, "question_id": str(question_id)})
        while True:
            remaining = expires_at - time.time()
            if remaining <= 0:
                await websocket.close(code=1008)
                return
            message = await asyncio.wait_for(websocket.receive(), timeout=min(60, remaining))
            if message["type"] == "websocket.disconnect":
                return
            await check_rate_limit(f"voice:{user_id}", 20)
            if message.get("bytes"):
                transcript = await VoiceService.transcribe_audio_bytes(message["bytes"])
                await websocket.send_json(
                    {"transcript": transcript, "is_final": True, "question_id": str(question_id)}
                )
            elif message.get("text") == "speak_question":
                await websocket.send_bytes(await VoiceService.synthesize_speech(question_text))
            else:
                await websocket.send_json({"error": "Send an audio clip or speak_question"})
    except AppError as exc:
        await websocket.send_json({"error": {"code": exc.error_code, "message": exc.message}})
        await websocket.close(code=1008 if exc.status_code in {401, 403, 409, 429} else 1011)
    except TimeoutError:
        await websocket.close(code=1008)
    except WebSocketDisconnect:
        return
