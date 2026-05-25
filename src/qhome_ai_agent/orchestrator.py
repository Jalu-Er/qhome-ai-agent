from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .agents import AGENTS
from .io_utils import append_jsonl, write_json
from .llm import ChatModel
from .models import RunState
from .report import write_markdown_report


def run_workflow(
    *,
    model: ChatModel,
    ticket: dict,
    knowledge_base: dict,
    output_dir: Path,
    run_id: str | None = None,
) -> dict:
    actual_run_id = run_id or f"run-{uuid4().hex[:8]}"
    run_dir = output_dir / actual_run_id
    state = RunState(run_id=actual_run_id, ticket=ticket, knowledge_base=knowledge_base)

    for agent in AGENTS:
        result = agent.run(model, state)
        state.add_step(agent.name, result)
        append_jsonl(
            run_dir / "interactions.jsonl",
            {
                "run_id": actual_run_id,
                "agent": agent.name,
                "display_name": agent.display_name,
                "output": result,
            },
        )

    final_output = state.final_output()
    write_json(run_dir / "final_output.json", final_output)
    write_markdown_report(run_dir / "report.md", final_output)
    return final_output
