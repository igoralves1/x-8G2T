"""Qdrant-backed vector store for the RAG knowledge base."""
from __future__ import annotations

from typing import Any

from loguru import logger
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qm

from ..core.config import settings


class VectorStore:
    def __init__(self) -> None:
        self.client = AsyncQdrantClient(url=settings.qdrant_url)
        self.collection = settings.rag_collection
        self.dim = settings.embed_dim

    async def ensure_collection(self) -> None:
        existing = {c.name for c in (await self.client.get_collections()).collections}
        if self.collection not in existing:
            await self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(size=self.dim, distance=qm.Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection '{self.collection}' (dim={self.dim})")

    async def upsert(self, points: list[dict[str, Any]]) -> None:
        """points: [{id, vector, payload}]"""
        await self.client.upsert(
            collection_name=self.collection,
            points=[
                qm.PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
                for p in points
            ],
        )

    async def search(self, vector: list[float], top_k: int | None = None,
                     device_filter: str | None = None,
                     domain: str | None = None) -> list[dict[str, Any]]:
        must = None
        should = None
        if domain:
            must = [qm.FieldCondition(key="domain", match=qm.MatchValue(value=domain))]
        if device_filter:
            should = [
                qm.FieldCondition(key="device_id", match=qm.MatchValue(value=device_filter)),
                qm.FieldCondition(key="scope", match=qm.MatchValue(value="global")),
            ]
        flt = qm.Filter(must=must, should=should) if (must or should) else None
        hits = await self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=top_k or settings.rag_top_k,
            query_filter=flt,
            with_payload=True,
        )
        return [{"score": h.score, **(h.payload or {})} for h in hits]

    async def count(self) -> int:
        try:
            return (await self.client.count(self.collection)).count
        except Exception:  # noqa: BLE001
            return 0


vector_store = VectorStore()
