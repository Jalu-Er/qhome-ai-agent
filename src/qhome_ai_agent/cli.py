from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_settings
from .io_utils import read_json
from .llm import SumoPodChatModel
from .mock_llm import MockChatModel
from .orchestrator import run_workflow


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run QHome customer support multi-agent workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-tickets", help="List available sample ticket IDs.")
    list_parser.add_argument("--tickets", default="data/sample_tickets.json")

    run_parser = subparsers.add_parser("run", help="Run the multi-agent workflow.")
    run_parser.add_argument("--ticket-id", default="damaged-ceramic-delivery")
    run_parser.add_argument("--ticket-text", help="Run with custom ticket message instead of sample ticket.")
    run_parser.add_argument("--customer-name", default="Pelanggan")
    run_parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    run_parser.add_argument("--tickets", default="data/sample_tickets.json")
    run_parser.add_argument("--knowledge-base", default="data/knowledge_base.json")
    run_parser.add_argument("--output-dir", default="runs")
    return parser


def load_ticket(root: Path, tickets_path: str, ticket_id: str) -> dict:
    tickets = read_json(root / tickets_path)
    for ticket in tickets:
        if ticket["id"] == ticket_id:
            return ticket
    available = ", ".join(ticket["id"] for ticket in tickets)
    raise SystemExit(f"Unknown ticket id: {ticket_id}. Available: {available}")


def command_list_tickets(args: argparse.Namespace) -> int:
    root = project_root()
    tickets = read_json(root / args.tickets)
    for ticket in tickets:
        print(f"{ticket['id']}: {ticket['subject']}")
    return 0


def command_run(args: argparse.Namespace) -> int:
    root = project_root()
    knowledge_base = read_json(root / args.knowledge_base)
    if args.ticket_text:
        ticket = {
            "id": "custom-ticket",
            "customer_name": args.customer_name,
            "channel": "cli",
            "subject": "Custom customer ticket",
            "message": args.ticket_text,
        }
    else:
        ticket = load_ticket(root, args.tickets, args.ticket_id)

    if args.mode == "live":
        settings = load_settings(root)
        model = SumoPodChatModel(settings=settings)
    else:
        model = MockChatModel()

    final_output = run_workflow(
        model=model,
        ticket=ticket,
        knowledge_base=knowledge_base,
        output_dir=root / args.output_dir,
    )

    final = final_output["final"]
    print(f"Run ID: {final_output['run_id']}")
    print(f"Intent: {final.get('intent')}")
    print(f"Priority: {final.get('priority')}")
    print(f"Escalate: {final.get('escalate')}")
    print(f"Output: {args.output_dir}/{final_output['run_id']}/final_output.json")
    print(f"Report: {args.output_dir}/{final_output['run_id']}/report.md")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list-tickets":
        raise SystemExit(command_list_tickets(args))
    if args.command == "run":
        raise SystemExit(command_run(args))
    raise SystemExit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
