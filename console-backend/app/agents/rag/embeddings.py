"""Real embeddings only; lexical search handles installations without AI."""

from openai import APIError, AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


async def embed_batch(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if not settings.OPENAI_API_KEY:
        raise ServiceUnavailableError("Embeddings require an OpenAI API key")
    try:
        async with AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY, timeout=30, max_retries=2
        ) as client:
            response = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
            return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
    except APIError as exc:
        raise ServiceUnavailableError("Embedding provider is unavailable") from exc


async def embed_text(text: str) -> list[float]:
    return (await embed_batch([text]))[0]
