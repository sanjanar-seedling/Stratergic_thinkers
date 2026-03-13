"""LLM Provider Abstraction — Swappable inference backend.

Supports:
- Ollama (local, free, default for testing — uses tinyllama)
- OpenAI (cloud, production — uses gpt-4o-mini)

Swap via config: LLM_PROVIDER=ollama or LLM_PROVIDER=openai
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        """Send a chat completion request. Returns response text."""
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for text."""
        ...


class OllamaProvider(LLMProvider):
    """Local Ollama inference — zero cost, no API key needed."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        chat_model: str = "tinyllama",
        embed_model: str = "nomic-embed-text",
    ):
        self.base_url = base_url
        self.chat_model = chat_model
        self.embed_model = embed_model

    async def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        """Call Ollama chat API."""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.chat_model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": temperature},
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "").strip()
        except httpx.ConnectError:
            logger.warning("Ollama not running. Returning fallback response.")
            return "[Ollama unavailable] Please start Ollama with: ollama serve"
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            return f"[LLM Error] {str(e)}"

    async def embed(self, text: str) -> list[float]:
        """Call Ollama embeddings API."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.embed_model, "prompt": text},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("embedding", [0.0] * 1536)
        except Exception as e:
            logger.warning(f"Ollama embedding failed: {e}")
            return [0.0] * 1536


class OpenAIProvider(LLMProvider):
    """OpenAI cloud inference — requires OPENAI_API_KEY."""

    def __init__(
        self,
        chat_model: str = "gpt-4o-mini",
        embed_model: str = "text-embedding-3-small",
    ):
        self.chat_model = chat_model
        self.embed_model = embed_model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI()
            except Exception as e:
                logger.error(f"OpenAI client init failed: {e}")
        return self._client

    async def chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        """Call OpenAI chat completion."""
        client = self._get_client()
        if client is None:
            return "[OpenAI unavailable] Set OPENAI_API_KEY in .env"

        try:
            response = await client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI chat failed: {e}")
            return f"[LLM Error] {str(e)}"

    async def embed(self, text: str) -> list[float]:
        """Call OpenAI embeddings API."""
        client = self._get_client()
        if client is None:
            return [0.0] * 1536

        try:
            response = await client.embeddings.create(
                model=self.embed_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            return [0.0] * 1536


# ── Factory ──

_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider (singleton)."""
    global _provider
    if _provider is None:
        provider_name = settings.llm_provider.lower()
        if provider_name == "openai":
            _provider = OpenAIProvider(
                chat_model=settings.chat_model,
                embed_model=settings.embedding_model,
            )
            logger.info(f"LLM Provider: OpenAI ({settings.chat_model})")
        else:
            _provider = OllamaProvider(
                base_url=settings.ollama_base_url,
                chat_model=settings.ollama_chat_model,
                embed_model=settings.ollama_embed_model,
            )
            logger.info(f"LLM Provider: Ollama ({settings.ollama_chat_model})")
    return _provider
