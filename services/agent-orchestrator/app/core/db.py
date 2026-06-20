"""Async PostgreSQL connection pool + helpers for agent persistence."""
from __future__ import annotations

import json
from typing import Any

import asyncpg
from loguru import logger

from .config import settings

_pool: asyncpg.Pool | None = None


async def connect() -> None:
    global _pool
    _pool = await asyncpg.create_pool(dsn=settings.pg_dsn, min_size=1, max_size=10)
    logger.info("PostgreSQL pool ready")


async def close() -> None:
    if _pool:
        await _pool.close()


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialised")
    return _pool


# --- Agent run persistence ---------------------------------------------------

async def create_run(objective: str, device_id: str | None, triggered_by: str) -> str:
    async with pool().acquire() as c:
        row = await c.fetchrow(
            """INSERT INTO agent_runs (objective, device_id, triggered_by)
               VALUES ($1, $2, $3) RETURNING run_id""",
            objective, device_id, triggered_by,
        )
    return str(row["run_id"])


async def add_step(run_id: str, idx: int, agent: str, thought: str | None,
                   tool: str | None, tool_input: dict | None, observation: str | None) -> None:
    async with pool().acquire() as c:
        await c.execute(
            """INSERT INTO agent_steps
               (run_id, step_index, agent_name, thought, tool_name, tool_input, observation)
               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            run_id, idx, agent, thought, tool,
            json.dumps(tool_input) if tool_input is not None else None, observation,
        )


async def finish_run(run_id: str, answer: str, status: str, steps: int, duration_ms: int) -> None:
    async with pool().acquire() as c:
        await c.execute(
            """UPDATE agent_runs
               SET final_answer=$2, status=$3, total_steps=$4, duration_ms=$5
               WHERE run_id=$1""",
            run_id, answer, status, steps, duration_ms,
        )


async def fetch(query: str, *args) -> list[dict[str, Any]]:
    async with pool().acquire() as c:
        rows = await c.fetch(query, *args)
    return [dict(r) for r in rows]


async def fetchrow(query: str, *args) -> dict[str, Any] | None:
    async with pool().acquire() as c:
        row = await c.fetchrow(query, *args)
    return dict(row) if row else None


async def execute(query: str, *args) -> None:
    async with pool().acquire() as c:
        await c.execute(query, *args)
