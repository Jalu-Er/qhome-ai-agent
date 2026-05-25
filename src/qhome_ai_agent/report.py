from __future__ import annotations

from pathlib import Path
from typing import Any


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "-"
    return str(value)


def write_markdown_report(path: Path, final_output: dict[str, Any]) -> None:
    final = final_output["final"]
    lines = [
        f"# Run Report: {final_output['run_id']}",
        "",
        "## Ticket",
        "",
        f"- Customer: {final_output['ticket'].get('customer_name', '-')}",
        f"- Subject: {final_output['ticket'].get('subject', '-')}",
        f"- Channel: {final_output['ticket'].get('channel', '-')}",
        "",
        "## Final Decision",
        "",
        f"- Intent: `{final.get('intent')}`",
        f"- Category: `{final.get('category')}`",
        f"- Priority: `{final.get('priority')}`",
        f"- Escalate: `{format_value(final.get('escalate'))}`",
        f"- Escalation Team: `{format_value(final.get('escalation_team'))}`",
        "",
        "## Customer Reply",
        "",
        final.get("customer_reply", "-"),
        "",
        "## Internal Next Steps",
        "",
    ]
    steps = final.get("internal_next_steps", [])
    if isinstance(steps, str):
        steps = [steps]
    for item in steps:
        lines.append(f"- {item}")

    lines.extend(["", "## Agent Trace", ""])
    for step in final_output["trace"]:
        lines.append(f"### {step['agent']}")
        lines.append("")
        lines.append(step["output"].get("reasoning", "No reasoning provided."))
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
