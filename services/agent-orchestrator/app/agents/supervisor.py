"""Supervisor agent: plans an investigation and delegates to specialists.

The supervisor is itself a ReAct agent, but its "tools" are the specialist
agents. Delegation tools are registered into the shared registry; they read the
current run id / step callback from contextvars so specialist sub-steps are
persisted under the same run and streamed to the caller.
"""
from __future__ import annotations

import contextvars

from ..core.config import settings
from ..tools import registry
from .base import Agent
from .definitions import SPECIALISTS

_current_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_id", default=None)
_current_on_step: contextvars.ContextVar = contextvars.ContextVar("on_step", default=None)


def _make_delegate(agent_name: str):
    async def _delegate(subtask: str) -> str:
        specialist = SPECIALISTS[agent_name]
        answer, _ = await specialist.run(
            subtask,
            run_id=_current_run_id.get(),
            on_step=_current_on_step.get(),
        )
        return answer
    return _delegate


# Register one delegation tool per specialist.
for _name, _agent in SPECIALISTS.items():
    registry._REGISTRY[f"ask_{_name}"] = registry.Tool(
        name=f"ask_{_name}",
        description=f"Delegate a focused sub-task to the {_name} specialist. "
                    f"Mission: {_agent.role.split('.')[0]}.",
        parameters={"subtask": {"type": "string",
                                "description": "a clear, self-contained instruction"}},
        required=["subtask"],
        func=_make_delegate(_name),
    )

supervisor = Agent(
    name="supervisor",
    role=(
        "You are the supervising AI operations manager for an industrial IoT "
        "site running on a Jetson edge server. You decompose the user's "
        "objective, delegate focused sub-tasks to the right specialist agents, "
        "and synthesise their findings into a single clear, actionable answer. "
        "Delegate telemetry/anomaly questions to the telemetry analyst, "
        "any statistical process control / control-chart / Six Sigma / process "
        "capability question to the SPC analyst, root-cause questions to the "
        "diagnostic engineer, image questions to the vision inspector, and any "
        "alarm-raising or memory-saving to the remediation agent. Do the analysis "
        "through your specialists rather than answering from assumptions."
    ),
    tools=[f"ask_{n}" for n in SPECIALISTS],
    max_steps=settings.agent_max_steps,
)


async def run_supervised(objective: str, run_id: str, on_step=None):
    """Execute the supervisor loop with run/step context bound."""
    _current_run_id.set(run_id)
    _current_on_step.set(on_step)
    return await supervisor.run(objective, run_id=run_id, on_step=on_step)
