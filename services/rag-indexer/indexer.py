#!/usr/bin/env python3
"""RAG indexer.

Walks the knowledge sources, splits documents into overlapping chunks, embeds
them on the GPU embeddings server, and upserts the vectors into Qdrant.
Two sources are indexed, each tagged with a `domain` so retrieval can be scoped:

  * KNOWLEDGE_BASE_DIR  (default /knowledge-base)  -> domain "ops"
  * BOOKS_DIR           (default /books)           -> domain "spc"
        the Statistical Process Control / Six Sigma reference books (PDF), which
        the specialized SPC agent retrieves with rag_search(domain='spc').

Document bookkeeping (sha256, chunk counts) is recorded in PostgreSQL so re-runs
are idempotent and only changed files are re-embedded.

Run it via:  docker compose --profile index run --rm rag-indexer
"""
from __future__ import annotations

import hashlib
import os
import sys
import uuid
from pathlib import Path

import httpx
import psycopg2
from loguru import logger
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

# --- Config from environment -------------------------------------------------
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "http://embeddings:8080/v1")
KB_DIR = Path(os.getenv("KNOWLEDGE_BASE_DIR", "/knowledge-base"))
BOOKS_DIR = Path(os.getenv("BOOKS_DIR", "/books"))
KB_DOMAIN = os.getenv("KB_DOMAIN", "ops")
BOOKS_DOMAIN = os.getenv("BOOKS_DOMAIN", "spc")
COLLECTION = os.getenv("RAG_COLLECTION", "x8g2t_knowledge")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
EMBED_BATCH = int(os.getenv("RAG_EMBED_BATCH", "32"))

PG = dict(
    host=os.getenv("POSTGRES_HOST", "postgres"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    user=os.getenv("POSTGRES_USER", "iot_admin"),
    password=os.getenv("POSTGRES_PASSWORD", ""),
    dbname=os.getenv("POSTGRES_DB", "iot_telemetry"),
)

TEXT_SUFFIXES = {".md", ".txt", ".rst", ".log", ".csv"}


def read_document(path: Path) -> str:
    """Extract text from a supported document (text formats or PDF)."""
    if path.suffix.lower() == ".pdf":
        try:
            reader = PdfReader(str(path))
            pages = [(pg.extract_text() or "") for pg in reader.pages]
            return "\n".join(pages)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"failed to read PDF {path.name}: {exc}")
            return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks, buf, length = [], [], 0
    for w in words:
        buf.append(w)
        length += len(w) + 1
        if length >= size:
            chunks.append(" ".join(buf))
            keep = " ".join(buf)[-overlap:]
            buf, length = ([keep] if keep else []), len(keep)
    if buf:
        chunks.append(" ".join(buf))
    return [c.strip() for c in chunks if c.strip()]


def embed(client: httpx.Client, texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i:i + EMBED_BATCH]
        r = client.post(f"{EMBED_BASE_URL}/embeddings",
                        json={"model": "local", "input": batch}, timeout=180.0)
        r.raise_for_status()
        rows = sorted(r.json()["data"], key=lambda d: d["index"])
        out.extend(row["embedding"] for row in rows)
    return out


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover(root: Path, domain: str) -> list[tuple[Path, str]]:
    if not root.exists():
        return []
    suffixes = TEXT_SUFFIXES | {".pdf"}
    return [(p, domain) for p in root.rglob("*") if p.suffix.lower() in suffixes]


def main() -> int:
    qdrant = QdrantClient(url=QDRANT_URL)
    if COLLECTION not in {c.name for c in qdrant.get_collections().collections}:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=qm.VectorParams(size=EMBED_DIM, distance=qm.Distance.COSINE),
        )
        logger.info(f"created collection {COLLECTION}")

    pg = psycopg2.connect(**PG)
    pg.autocommit = True
    cur = pg.cursor()
    http = httpx.Client()

    files = discover(KB_DIR, KB_DOMAIN) + discover(BOOKS_DIR, BOOKS_DOMAIN)
    logger.info(f"found {len(files)} document(s) to consider "
                f"({KB_DIR}=ops, {BOOKS_DIR}=spc)")

    total_chunks = 0
    for path, domain in sorted(files, key=lambda t: str(t[0])):
        digest = sha256_of(path)
        cur.execute("SELECT chunk_count FROM rag_documents WHERE sha256=%s", (digest,))
        if cur.fetchone():
            logger.info(f"skip (unchanged): {path.name}")
            continue

        text = read_document(path)
        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            logger.warning(f"no extractable text: {path.name} (scanned PDF? needs OCR)")
            continue

        # Optional metadata header convention for text files: "device:sensor_001".
        scope, device_id = "global", None
        first = text.strip().splitlines()[0] if text.strip() else ""
        if first.lower().startswith("device:"):
            device_id = first.split(":", 1)[1].strip()
            scope = "device"

        logger.info(f"embedding {path.name}: {len(chunks)} chunks (domain={domain})")
        vectors = embed(http, chunks)
        base = KB_DIR if domain == KB_DOMAIN else BOOKS_DIR
        rel = str(path.relative_to(base)) if base in path.parents or base == path.parent else path.name
        points = [
            qm.PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={"text": chunk, "title": path.stem, "source_path": rel,
                         "domain": domain, "scope": scope, "device_id": device_id,
                         "chunk_index": i},
            )
            for i, (chunk, vec) in enumerate(zip(chunks, vectors))
        ]
        # Upsert in batches to keep request sizes reasonable.
        for i in range(0, len(points), 256):
            qdrant.upsert(collection_name=COLLECTION, points=points[i:i + 256])

        cur.execute(
            """INSERT INTO rag_documents (source_path, title, sha256, chunk_count)
               VALUES (%s,%s,%s,%s)
               ON CONFLICT (sha256) DO UPDATE SET chunk_count=EXCLUDED.chunk_count,
               indexed_at=NOW()""",
            (rel, path.stem, digest, len(points)))
        total_chunks += len(points)
        logger.info(f"indexed {path.name}: {len(points)} chunks (domain={domain})")

    logger.info(f"done. {total_chunks} new chunks indexed into '{COLLECTION}'.")
    cur.close(); pg.close(); http.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
