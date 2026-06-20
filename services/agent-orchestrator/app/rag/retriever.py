"""RAG retriever: embed a query, search Qdrant, return formatted context."""
from __future__ import annotations

from ..core.llm_clients import embedder
from .vectorstore import vector_store


async def retrieve(query: str, top_k: int | None = None,
                   device_id: str | None = None,
                   domain: str | None = None) -> list[dict]:
    """Return the top matching knowledge-base chunks for a query."""
    qvec = await embedder.embed_one(query)
    return await vector_store.search(qvec, top_k=top_k, device_filter=device_id,
                                     domain=domain)


def format_context(chunks: list[dict]) -> str:
    """Render retrieved chunks into a citable context block for the LLM."""
    if not chunks:
        return "No relevant knowledge-base documents were found."
    lines = []
    for i, ch in enumerate(chunks, start=1):
        src = ch.get("title") or ch.get("source_path") or "unknown"
        score = ch.get("score", 0.0)
        text = (ch.get("text") or "").strip()
        lines.append(f"[{i}] (source: {src}, relevance: {score:.2f})\n{text}")
    return "\n\n".join(lines)


async def retrieve_and_format(query: str, top_k: int | None = None,
                              device_id: str | None = None,
                              domain: str | None = None) -> tuple[str, list[dict]]:
    chunks = await retrieve(query, top_k=top_k, device_id=device_id, domain=domain)
    return format_context(chunks), chunks
