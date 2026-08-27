"""Evaluation harness runner (Task 3).

Runs every Task 1 and Task 2 case, scores it, and writes eval_report.json
(and a Markdown summary) documenting individual + aggregate results. Never
hides a failing case -- every case's score and pass/fail state is written
to the report regardless of outcome.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agents.account_health_agent import run_account_health
from src.agents.triage_agent import run_triage
from src.config.settings import settings
from src.evaluation.cases_task1 import build_task1_cases
from src.evaluation.cases_task2 import build_task2_cases
from src.evaluation.guardrail_cases import build_guardrail_cases
from src.evaluation.scoring import PASS_THRESHOLD, score_task1, score_task2
from src.models.triage import TicketInput
from src.services.data_loader import get_data_store

APP_VERSION = "0.1.0"


def _run_task1_case(case: dict[str, Any]) -> dict[str, Any]:
    ticket_input = TicketInput(**case["input"])
    llm_client = case["llm_client_factory"]() if case.get("llm_client_factory") else None
    try:
        result = run_triage(ticket_input, llm_client=llm_client)
    except Exception as exc:  # noqa: BLE001 - eval harness must record, not raise
        return {
            "id": case["id"],
            "description": case["description"],
            "passed": False,
            "score": 0.0,
            "components": {},
            "failure_reason": f"Pipeline raised an exception: {exc!r}",
        }

    breakdown = score_task1(result, case.get("expected", {}))
    passed = breakdown.total >= PASS_THRESHOLD
    failure_reason = None
    if not passed:
        worst = min(breakdown.components, key=lambda k: breakdown.components[k])
        failure_reason = f"Lowest-scoring component: {worst} ({breakdown.components[worst]})"
    return {
        "id": case["id"],
        "description": case["description"],
        "passed": passed,
        "score": breakdown.total,
        "components": breakdown.components,
        "failure_reason": failure_reason,
        "output_summary": {
            "urgency": result.classification.urgency,
            "category": result.classification.category,
            "team": result.routing.recommended_team,
            "known_issue": result.knowledge_base.known_issue,
        },
    }


def _run_task2_case(case: dict[str, Any]) -> dict[str, Any]:
    store = get_data_store()
    account_id = case["input"]["account_id"]
    llm_client = case["llm_client_factory"]() if case.get("llm_client_factory") else None
    try:
        brief = run_account_health(account_id, llm_client=llm_client)
    except Exception as exc:  # noqa: BLE001
        return {
            "id": case["id"],
            "description": case["description"],
            "passed": False,
            "score": 0.0,
            "components": {},
            "failure_reason": f"Pipeline raised an exception: {exc!r}",
        }

    ticket_bodies = {t.ticket_id: f"{t.subject}\n{t.body}" for t in store.tickets}
    account = store.get_account(account_id)
    account_notes = account.escalation_notes if account else []

    breakdown = score_task2(brief, case.get("expected", {}), ticket_bodies, account_notes)
    passed = breakdown.total >= PASS_THRESHOLD
    failure_reason = None
    if not passed:
        worst = min(breakdown.components, key=lambda k: breakdown.components[k])
        failure_reason = f"Lowest-scoring component: {worst} ({breakdown.components[worst]})"
    return {
        "id": case["id"],
        "description": case["description"],
        "passed": passed,
        "score": breakdown.total,
        "components": breakdown.components,
        "failure_reason": failure_reason,
        "output_summary": {
            "account_found": brief.metadata.account_found,
            "tickets_considered": brief.metadata.tickets_considered,
            "risks_flagged": len(brief.risks),
        },
    }


def run_evaluation() -> dict[str, Any]:
    task1_results = [_run_task1_case(c) for c in build_task1_cases()]
    task2_results = [_run_task2_case(c) for c in build_task2_cases()]

    guardrail_cases = build_guardrail_cases()
    guardrail1_results = [_run_task1_case(c) for c in guardrail_cases["task1"]]
    guardrail2_results = [_run_task2_case(c) for c in guardrail_cases["task2"]]

    task1_avg = round(sum(r["score"] for r in task1_results) / len(task1_results), 4) if task1_results else 0.0
    task2_avg = round(sum(r["score"] for r in task2_results) / len(task2_results), 4) if task2_results else 0.0
    guardrail_all = guardrail1_results + guardrail2_results
    guardrail_avg = round(sum(r["score"] for r in guardrail_all) / len(guardrail_all), 4) if guardrail_all else 0.0
    overall = (
        round((task1_avg + task2_avg + guardrail_avg) / 3, 4)
        if (task1_results and task2_results and guardrail_all)
        else 0.0
    )

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app_version": APP_VERSION,
        "llm_provider": settings.llm_provider,
        "prompt_versions": {"triage": "triage_v1", "account_health": "account_health_v1"},
        "pass_threshold": PASS_THRESHOLD,
        "task1": {
            "cases": task1_results,
            "aggregate_score": task1_avg,
            "pass_count": sum(1 for r in task1_results if r["passed"]),
            "total_count": len(task1_results),
        },
        "task2": {
            "cases": task2_results,
            "aggregate_score": task2_avg,
            "pass_count": sum(1 for r in task2_results if r["passed"]),
            "total_count": len(task2_results),
        },
        "guardrails": {
            "description": (
                "Adversarial 'bad LLM' cases: each injects a deliberately misbehaving "
                "LLM client and asserts the deterministic guardrail layer, not the model, "
                "produced the correct final result."
            ),
            "cases": guardrail1_results + guardrail2_results,
            "aggregate_score": guardrail_avg,
            "pass_count": sum(1 for r in guardrail_all if r["passed"]),
            "total_count": len(guardrail_all),
        },
        "overall_score": overall,
    }
    return report


def write_report(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "eval_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Evaluation Report",
        "",
        f"- Timestamp: {report['timestamp']}",
        f"- LLM provider: {report['llm_provider']}",
        f"- Overall score: **{report['overall_score']}**",
        "",
        f"## Task 1 -- Triage ({report['task1']['pass_count']}/{report['task1']['total_count']} passed, "
        f"avg score {report['task1']['aggregate_score']})",
        "",
        "| Case | Passed | Score | Notes |",
        "|---|---|---|---|",
    ]
    for r in report["task1"]["cases"]:
        lines.append(f"| {r['id']} | {'✅' if r['passed'] else '❌'} | {r['score']} | {r['failure_reason'] or '-'} |")

    lines += [
        "",
        f"## Task 2 -- Account Health ({report['task2']['pass_count']}/{report['task2']['total_count']} passed, "
        f"avg score {report['task2']['aggregate_score']})",
        "",
        "| Case | Passed | Score | Notes |",
        "|---|---|---|---|",
    ]
    for r in report["task2"]["cases"]:
        lines.append(f"| {r['id']} | {'✅' if r['passed'] else '❌'} | {r['score']} | {r['failure_reason'] or '-'} |")

    lines += [
        "",
        f"## Guardrails -- adversarial 'bad LLM' cases ({report['guardrails']['pass_count']}/"
        f"{report['guardrails']['total_count']} passed, avg score {report['guardrails']['aggregate_score']})",
        "",
        report["guardrails"]["description"],
        "",
        "| Case | Passed | Score | Notes |",
        "|---|---|---|---|",
    ]
    for r in report["guardrails"]["cases"]:
        lines.append(f"| {r['id']} | {'✅' if r['passed'] else '❌'} | {r['score']} | {r['failure_reason'] or '-'} |")

    (out_dir / "eval_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    from src.config.settings import REPO_ROOT

    report = run_evaluation()
    write_report(report, REPO_ROOT)
    print(json.dumps({"overall_score": report["overall_score"]}, indent=2))
