"""Bounded, validated completions shared by AI services."""

import json
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TypeVar

import httpx
from openai import APIError, AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    @abstractmethod
    async def generate_text(self, prompt: str, *, system: str | None = None) -> str:
        """Return text or raise a service error."""

    async def generate_structured(
        self, prompt: str, *, response_model: type[T], system: str | None = None
    ) -> T:
        schema = json.dumps(response_model.model_json_schema())
        text = await self.generate_text(
            prompt, system=f"{system or ''} Return only JSON matching this schema: {schema}"
        )
        try:
            return response_model.model_validate_json(text)
        except ValidationError as exc:
            raise ServiceUnavailableError("AI provider returned an invalid response") from exc


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=2)
        self.model = model

    async def generate_text(self, prompt: str, *, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            result = await self.client.chat.completions.create(
                model=self.model, messages=messages, max_tokens=4096
            )
            choice = result.choices[0]
            if choice.finish_reason != "stop" or not choice.message.content:
                raise ServiceUnavailableError("AI provider could not complete the response")
            return choice.message.content
        except APIError as exc:
            raise ServiceUnavailableError("AI provider is unavailable") from exc


class AnthropicProvider(LLMProvider):
    async def generate_text(self, prompt: str, *, system: str | None = None) -> str:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "max_tokens": 4096,
                        "system": system or "",
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
                body = response.json()
                if body.get("stop_reason") != "end_turn":
                    raise ValueError("Incomplete response")
                return "".join(c["text"] for c in body["content"] if c["type"] == "text")
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ServiceUnavailableError("AI provider is unavailable") from exc


@lru_cache
def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return OpenAIProvider(settings.OPENAI_API_KEY, settings.LLM_MODEL)
    if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicProvider()
    if settings.LLM_PROVIDER == "local" and settings.LOCAL_LLM_BASE_URL:
        return OpenAIProvider("local", settings.LLM_MODEL, settings.LOCAL_LLM_BASE_URL)
    raise ServiceUnavailableError("AI provider is not configured")
