"""Bounded speech requests with explicit provider failures."""

from openai import APIError, AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError, ValidationAppError


class VoiceService:
    @classmethod
    def _get_client(cls) -> AsyncOpenAI:
        if not settings.OPENAI_API_KEY:
            raise ServiceUnavailableError("Speech provider is not configured")
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=30, max_retries=1)

    @classmethod
    async def transcribe_audio_bytes(cls, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        if not audio_bytes or len(audio_bytes) > settings.MAX_UPLOAD_BYTES:
            raise ValidationAppError("Audio is empty or exceeds the upload limit")
        try:
            async with cls._get_client() as client:
                result = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=(filename, audio_bytes),
                )
                return result.text
        except APIError as exc:
            raise ServiceUnavailableError("Speech transcription failed") from exc

    @classmethod
    async def synthesize_speech(cls, text: str, voice: str = "alloy") -> bytes:
        if not text.strip() or len(text) > 4096:
            raise ValidationAppError("Speech text must contain 1-4096 characters")
        try:
            async with cls._get_client() as client:
                response = await client.audio.speech.create(model="tts-1", voice=voice, input=text)
                return response.content
        except APIError as exc:
            raise ServiceUnavailableError("Speech synthesis failed") from exc
