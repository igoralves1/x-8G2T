"""Thin async clients for the llama.cpp OpenAI-compatible inference servers.

Three endpoints, one protocol:
  * LLM   -> /v1/chat/completions   (text reasoning, used by every agent)
  * VLM   -> /v1/chat/completions   (multimodal, image_url content parts)
  * Embed -> /v1/embeddings         (RAG ingest + retrieval)
"""
from __future__ import annotations

import base64
from typing import Any

import httpx
from loguru import logger

from .config import settings

_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


class LLMClient:
    """Chat completion client for the text reasoning model."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")

    async def chat(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> str:
        payload = {
            "model": "local",
            "messages": messages,
            "temperature": settings.agent_temperature if temperature is None else temperature,
            "max_tokens": max_tokens,
        }
        if stop:
            payload["stop"] = stop
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(f"{self.base_url}/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]


class VLMClient:
    """Vision-language client. Accepts a local image path or raw bytes."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.vlm_base_url).rstrip("/")

    @staticmethod
    def _encode(image_bytes: bytes, mime: str = "image/jpeg") -> str:
        b64 = base64.b64encode(image_bytes).decode()
        return f"data:{mime};base64,{b64}"

    async def analyze(self, image_bytes: bytes, prompt: str, mime: str = "image/jpeg") -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": self._encode(image_bytes, mime)}},
                ],
            }
        ]
        payload = {"model": "local", "messages": messages, "max_tokens": 512, "temperature": 0.2}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(f"{self.base_url}/chat/completions", json=payload)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]


class EmbeddingClient:
    """Embedding client used by the RAG retriever and the indexer."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.embed_base_url).rstrip("/")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": "local", "input": texts}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(f"{self.base_url}/embeddings", json=payload)
            r.raise_for_status()
            data = r.json()
        # Preserve input order.
        rows = sorted(data["data"], key=lambda d: d["index"])
        return [row["embedding"] for row in rows]

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]


async def health(base_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base_url.rstrip('/').removesuffix('/v1')}/health")
            return r.status_code == 200
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"health check failed for {base_url}: {exc}")
        return False


llm = LLMClient()
vlm = VLMClient()
embedder = EmbeddingClient()
