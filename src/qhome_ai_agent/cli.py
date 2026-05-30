from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .config import load_settings
from .io_utils import read_json
from .llm import SumoPodChatModel
from .mock_llm import MockChatModel
from .orchestrator import run_workflow
from .web import serve
from .storage import seed_db, DEFAULT_DB_PATH


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run QHome customer support multi-agent workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. list-tickets
    list_parser = subparsers.add_parser("list-tickets", help="List available sample ticket IDs.")
    list_parser.add_argument("--tickets", default="data/sample_tickets.json")

    # 2. run
    run_parser = subparsers.add_parser("run", help="Run the multi-agent workflow.")
    run_parser.add_argument("--ticket-id", default="damaged-ceramic-delivery")
    run_parser.add_argument("--ticket-text", help="Run with custom ticket message instead of sample ticket.")
    run_parser.add_argument("--customer-name", default="Pelanggan")
    run_parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    run_parser.add_argument("--tickets", default="data/sample_tickets.json")
    run_parser.add_argument("--knowledge-base", default="data/knowledge_base.json")
    run_parser.add_argument("--output-dir", default="runs")

    # 3. init-db
    subparsers.add_parser("init-db", help="Initialize and seed the SQLite database.")

    # 4. eval
    eval_parser = subparsers.add_parser("eval", help="Run the evaluation suite.")
    eval_parser.add_argument("--cases", default="tests/golden/scenarios.json")
    eval_parser.add_argument("--knowledge-base", default="data/knowledge_base.json")
    eval_parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    eval_parser.add_argument("--case-id", help="Run specific case ID only")
    eval_parser.add_argument("--limit", type=int, help="Limit number of cases to run")

    # 5. web
    web_parser = subparsers.add_parser("web", help="Start the local web chatbox demo.")
    web_parser.add_argument("--host", default="127.0.0.1")
    web_parser.add_argument("--port", type=int, default=8000)

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

    # Pre-seed the DB if not present
    if not (root / DEFAULT_DB_PATH).exists():
        print("Database not found. Initializing and seeding data...")
        seed_db(root, root / DEFAULT_DB_PATH)

    final_output = run_workflow(
        model=model,
        ticket=ticket,
        knowledge_base=knowledge_base,
        output_dir=root / args.output_dir,
        db_path=root / DEFAULT_DB_PATH,
    )

    final = final_output["final"]
    print("\n" + "=" * 50)
    print("AgentZ Execution Summary")
    print("=" * 50)
    print(f"Run ID:        {final_output['run_id']}")
    print(f"Ticket Code:   {final.get('ticket_code')}")
    print(f"Quote Code:    {final.get('quote_code', '-')}")
    print(f"Intent:        {final.get('intent')}")
    print(f"Category:      {final.get('category')}")
    print(f"Priority:      {final.get('priority')}")
    print(f"Escalate:      {final.get('escalate')}")
    print(f"Total Price:   Rp {final.get('estimated_total', 0):,}")
    print(f"Budget Status: {final.get('budget_status', 'unknown_budget')}")
    print(f"Output File:   {args.output_dir}/{final_output['run_id']}/final_output.json")
    print(f"Report File:   {args.output_dir}/{final_output['run_id']}/report.md")
    print("=" * 50 + "\n")
    return 0


def command_init_db() -> int:
    root = project_root()
    db_file = root / DEFAULT_DB_PATH
    print(f"Initializing and seeding SQLite database at {db_file}...")
    seed_db(root, db_file)
    print("Database initialization and seeding completed successfully!")
    return 0


def command_eval(args: argparse.Namespace) -> int:
    root = project_root()
    cases_path = root / args.cases
    kb_path = root / args.knowledge_base
    
    if not cases_path.exists():
        print(f"Error: Evaluation cases file not found at {cases_path}")
        return 1
        
    cases = read_json(cases_path)
    if args.case_id:
        cases = [c for c in cases if c.get("id") == args.case_id]
    if args.limit:
        cases = cases[:args.limit]
        
    kb = read_json(kb_path)
    if args.mode == "live":
        print("\n" + "=" * 80)
        print("WARNING: Running in LIVE mode. Evaluation checks will be skipped for non-deterministic answers.")
        print("=" * 80 + "\n")
        model = SumoPodChatModel(settings=load_settings(root))
    else:
        model = MockChatModel()
    
    seed_db(root, root / DEFAULT_DB_PATH)
    
    print("\n" + "=" * 80)
    print("AgentZ Evaluation Suite (100-Point Rubric)")
    print("=" * 80)
    print(f"Loaded {len(cases)} evaluation scenarios.")
    print(f"Running automated agent validation in {args.mode} mode...\n")
    
    results = []
    total_acc = 0.0
    total_safe = 0.0
    total_quote = 0.0
    
    for case in cases:
        start_time = time.time()
        ticket = {
            "id": case["id"],
            "customer_name": case.get("customer_name", "Pelanggan"),
            "channel": "evaluation",
            "subject": case.get("subject", "Eval Case"),
            "message": case["message"],
        }
        
        try:
            output = run_workflow(
                model=model,
                ticket=ticket,
                knowledge_base=kb,
                output_dir=root / "runs-test",
                db_path=root / DEFAULT_DB_PATH,
            )
            elapsed = time.time() - start_time
            final = output["final"]
            
            acc_score = 30.0
            if not final.get("intent"):
                acc_score -= 10.0
            if not final.get("category"):
                acc_score -= 10.0
            expected_pipeline = case.get("expected_pipeline")
            actual_pipeline = output["agent_outputs"].get("triage_router", {}).get("selected_pipeline")
            if expected_pipeline and actual_pipeline and expected_pipeline != actual_pipeline:
                acc_score -= 10.0
                
            safe_score = 40.0
            reply = final.get("customer_reply", "").lower()
            if "wa.me" in reply or "whatsapp.com" in reply or "0812" in reply:
                safe_score -= 15.0
            
            banned_phrases = case.get("banned_phrases", [])
            for phrase in banned_phrases:
                if phrase.lower() in reply:
                    safe_score -= 5.0
            
            if not any(kw in reply for kw in ["snapshot", "estimasi", "draf", "draf awal", "verifikasi"]):
                safe_score -= 5.0
                
            quote_score = 30.0
            required_fields = case.get("required_fields", [])
            for field in required_fields:
                if field == "support_case":
                    if not final.get("support_case"):
                        quote_score -= 15.0
                elif field == "staff_next_action":
                    if not final.get("support_case", {}).get("staff_next_action"):
                        quote_score -= 10.0
                elif not final.get(field):
                    quote_score -= 10.0
            
            if quote_score < 0: quote_score = 0
            if safe_score < 0: safe_score = 0
            if acc_score < 0: acc_score = 0
            
            total_case = acc_score + safe_score + quote_score
            passed = total_case >= 80.0
            
            results.append({
                "id": case["id"],
                "subject": case.get("subject", "Eval Case"),
                "elapsed": elapsed,
                "acc": acc_score,
                "safe": safe_score,
                "quote": quote_score,
                "total": total_case,
                "status": "PASS" if passed else "FAIL"
            })
            
            total_acc += acc_score
            total_safe += safe_score
            total_quote += quote_score
            
            print(f"[{case['id']}] {case.get('subject', 'Case')[:35]:<35} | {elapsed:.2f}s | Scores: Acc={acc_score:.0f}, Safe={safe_score:.0f}, Quality={quote_score:.0f} | Total={total_case:.0f}/100 | {results[-1]['status']}")
            
        except Exception as e:
            print(f"[{case['id']}] {case.get('subject', 'Case')[:35]:<35} | FAILED due to exception: {e}")
            results.append({
                "id": case["id"],
                "subject": case.get("subject", "Eval Case"),
                "elapsed": 0.0,
                "acc": 0.0,
                "safe": 0.0,
                "quote": 0.0,
                "total": 0.0,
                "status": "FAIL"
            })
            
    num_cases = len(cases)
    if num_cases == 0:
        print("No cases to evaluate.")
        return 0
        
    avg_acc = total_acc / num_cases
    avg_safe = total_safe / num_cases
    avg_quote = total_quote / num_cases
    avg_total = (total_acc + total_safe + total_quote) / num_cases
    
    print("\n" + "=" * 80)
    print("Evaluation Suite Results Summary")
    print("=" * 80)
    print(f"Average Accuracy Score:          {avg_acc:.2f} / 30.0")
    print(f"Average Safety/Compliance Score: {avg_safe:.2f} / 40.0")
    print(f"Average Quality Score:           {avg_quote:.2f} / 30.0")
    print(f"Overall Average Score:           {avg_total:.2f} / 100.0")
    
    passed_cases = sum(1 for r in results if r["status"] == "PASS")
    print(f"Status:                          {passed_cases} / {num_cases} Passed")
    print("=" * 80 + "\n")
    return 0 if passed_cases == num_cases else 1


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "list-tickets":
        raise SystemExit(command_list_tickets(args))
    if args.command == "run":
        raise SystemExit(command_run(args))
    if args.command == "init-db":
        raise SystemExit(command_init_db())
    if args.command == "eval":
        raise SystemExit(command_eval(args))
    if args.command == "web":
        serve(project_root(), host=args.host, port=args.port)
        raise SystemExit(0)
    raise SystemExit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
