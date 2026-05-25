from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class AgentStep:
    agent: str
    output: dict[str, Any]
    timestamp: str = field(default_factory=utc_now)


@dataclass
class RunState:
    run_id: str
    ticket: dict[str, Any]
    knowledge_base: dict[str, Any]
    steps: list[AgentStep] = field(default_factory=list)

    def add_step(self, agent: str, output: dict[str, Any]) -> None:
        self.steps.append(AgentStep(agent=agent, output=output))

    def latest_outputs(self) -> dict[str, Any]:
        return {step.agent: step.output for step in self.steps}

    def to_context(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "ticket": self.ticket,
            "agent_outputs": self.latest_outputs(),
        }

    def final_output(self) -> dict[str, Any]:
        latest = self.latest_outputs()
        final_response = normalize_final_response(latest.get("qa_final_response", {}))
        return {
            "run_id": self.run_id,
            "ticket": self.ticket,
            "final": final_response,
            "agent_outputs": latest,
            "trace": [
                {
                    "agent": step.agent,
                    "timestamp": step.timestamp,
                    "output": step.output,
                }
                for step in self.steps
            ],
        }


def normalize_final_response(value: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(value)

    steps = normalized.get("internal_next_steps", [])
    if isinstance(steps, str):
        normalized["internal_next_steps"] = [steps]
    elif not isinstance(steps, list):
        normalized["internal_next_steps"] = [str(steps)]

    priority = normalized.get("priority")
    if isinstance(priority, str):
        lowered = priority.strip().lower()
        priority_map = {
            "tinggi": "high",
            "sedang": "medium",
            "menengah": "medium",
            "rendah": "low",
        }
        normalized["priority"] = priority_map.get(lowered, lowered)

    return normalized
