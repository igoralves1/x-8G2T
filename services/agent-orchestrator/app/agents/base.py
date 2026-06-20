"""Base ReAct-style agent.

Each agent owns a role (system prompt) and a subset of the tool registry.
It runs a bounded think -> act -> observe loop against the LLM server until it
produces a final answer or hits the step budget. Every step is streamed back
to the caller and persisted to `agent_steps` for auditability.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from loguru import logger

from ..core.config import settings
from ..core.llm_clients import llm
from ..tools import registry

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict | None:
    """Best-effort extraction of the first JSON object in a model response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):]
    m = _JSON_RE.search(text)
    if not m:
        return None
    snippet = m.group(0)
    for candidate in (snippet, snippet[: snippet.rfind("}") + 1]):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


_PROTOCOL = """\
You operate in a strict loop. At every turn reply with a SINGLE JSON object and nothing else.

To use a tool:
{"thought": "<your reasoning>", "action": {"tool": "<tool_name>", "args": {<arguments>}}}

When you have enough information to answer, finish with:
{"thought": "<your reasoning>", "final_answer": "<the complete answer>"}

Rules:
- Use only the tools listed below. Never invent tool names or arguments.
- Ground every factual claim in tool observations or retrieved documents.
- Prefer rag_search / recall_memory before guessing.
- Keep going until you can give a well-supported final_answer.
"""


@dataclass
class AgentStep:
    index: int
    agent: str
    thought: str | None = None
    tool: str | None = None
    tool_input: dict | None = None
    observation: str | None = None
    final_answer: str | None = None


@dataclass
class Agent:
    name: str
    role: str                      # system-prompt persona / mission
    tools: list[str] = field(default_factory=list)
    max_steps: int | None = None

    def _system_prompt(self) -> str:
        tool_block = json.dumps(registry.specs(self.tools), indent=2)
        return f"{self.role}\n\n{_PROTOCOL}\nAVAILABLE TOOLS:\n{tool_block}"

    async def run(self, objective: str, run_id: str | None = None,
                  on_step=None) -> tuple[str, list[AgentStep]]:
        budget = self.max_steps or settings.agent_max_steps
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": objective},
        ]
        steps: list[AgentStep] = []

        for i in range(budget):
            raw = await llm.chat(messages, max_tokens=1024)
            parsed = _extract_json(raw)

            if not parsed:
                # Nudge the model back into protocol once, else bail out.
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user",
                                 "content": "Respond with a single valid JSON object only."})
                continue

            thought = parsed.get("thought")

            if "final_answer" in parsed:
                step = AgentStep(i, self.name, thought=thought,
                                 final_answer=str(parsed["final_answer"]))
                steps.append(step)
                if on_step:
                    await on_step(step)
                await self._persist(run_id, step)
                return step.final_answer, steps

            action = parsed.get("action") or {}
            tool_name = action.get("tool")
            args = action.get("args", {}) or {}

            observation = await registry.dispatch(tool_name, args) if tool_name \
                else "ERROR: no tool specified and no final_answer given."

            step = AgentStep(i, self.name, thought=thought, tool=tool_name,
                             tool_input=args, observation=observation)
            steps.append(step)
            if on_step:
                await on_step(step)
            await self._persist(run_id, step)

            messages.append({"role": "assistant", "content": json.dumps(parsed)})
            messages.append({"role": "user",
                             "content": f"Observation from {tool_name}:\n{observation}"})

        # Step budget exhausted: ask for a best-effort summary.
        messages.append({"role": "user",
                         "content": "Step budget reached. Give your best final_answer now as JSON."})
        raw = await llm.chat(messages, max_tokens=1024)
        parsed = _extract_json(raw) or {}
        answer = str(parsed.get("final_answer", raw)).strip()
        step = AgentStep(len(steps), self.name, final_answer=answer)
        steps.append(step)
        await self._persist(run_id, step)
        return answer, steps

    @staticmethod
    async def _persist(run_id: str | None, step: AgentStep) -> None:
        if not run_id:
            return
        from ..core import db
        try:
            await db.add_step(run_id, step.index, step.agent, step.thought,
                              step.tool, step.tool_input,
                              step.observation or step.final_answer)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"could not persist step: {exc}")
