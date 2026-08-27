#!/usr/bin/env python3
"""Single CLI entry point for the Zycus AI support project.

Usage:
    python app.py triage --file examples/ticket.json
    python app.py triage --subject "..." --body "..."
    python app.py account-health --account-id ACC-3336
    python app.py eval
    python app.py serve
"""
from __future__ import annotations

import argparse
import json
import sys

from src.agents.account_health_agent import run_account_health
from src.agents.triage_agent import run_triage
from src.config.settings import REPO_ROOT
from src.models.triage import TicketInput


def cmd_triage(args: argparse.Namespace) -> None:
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
        ticket_input = TicketInput(**data)
    else:
        if not args.body:
            print("Error: provide --file or --subject/--body", file=sys.stderr)
            sys.exit(1)
        ticket_input = TicketInput(subject=args.subject or "", body=args.body, ticket_id=args.ticket_id)

    result = run_triage(ticket_input)
    print(result.model_dump_json(indent=2))


def cmd_account_health(args: argparse.Namespace) -> None:
    brief = run_account_health(args.account_id, reference_date=args.reference_date)
    print(brief.model_dump_json(indent=2))


def cmd_eval(_args: argparse.Namespace) -> None:
    from src.evaluation.runner import run_evaluation, write_report

    report = run_evaluation()
    write_report(report, REPO_ROOT)
    print(f"Overall score: {report['overall_score']}")
    print(f"Task 1: {report['task1']['pass_count']}/{report['task1']['total_count']} passed")
    print(f"Task 2: {report['task2']['pass_count']}/{report['task2']['total_count']} passed")
    print(f"Report written to {REPO_ROOT / 'eval_report.json'} and eval_report.md")


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=args.port, reload=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Zycus AI Support CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_triage = sub.add_parser("triage", help="Run the triage pipeline on a ticket")
    p_triage.add_argument("--file", help="Path to a JSON file with subject/body")
    p_triage.add_argument("--subject", help="Ticket subject")
    p_triage.add_argument("--body", help="Ticket body")
    p_triage.add_argument("--ticket-id", dest="ticket_id", default=None)
    p_triage.set_defaults(func=cmd_triage)

    p_acc = sub.add_parser("account-health", help="Generate an account health brief")
    p_acc.add_argument("--account-id", required=True)
    p_acc.add_argument("--reference-date", dest="reference_date", default=None, help="ISO date to anchor the 90-day window (defaults to the fixed dataset reference date for reproducibility)")
    p_acc.set_defaults(func=cmd_account_health)

    p_eval = sub.add_parser("eval", help="Run the evaluation harness")
    p_eval.set_defaults(func=cmd_eval)

    p_serve = sub.add_parser("serve", help="Run the FastAPI service")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
