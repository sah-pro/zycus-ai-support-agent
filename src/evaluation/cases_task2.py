"""Task 2 (account health) evaluation cases.

Built from real accounts.json records. Note a key dataset finding: only 4 of
484 unique ticket account_ids actually resolve to an accounts.json record,
so "account exists but has no linked tickets in-window" is not an edge case
here -- it is the dominant real-world case, and is tested explicitly.
"""
from __future__ import annotations

from typing import Any

from src.services.data_loader import get_data_store


def _find_account(predicate) -> dict[str, Any]:
    store = get_data_store()
    for a in store.accounts:
        if predicate(a):
            return a.model_dump()
    raise ValueError("No matching account found for this test case predicate.")


def build_task2_cases() -> list[dict[str, Any]]:
    store = get_data_store()

    healthy = _find_account(lambda a: a.health_status == "Healthy")
    at_risk = _find_account(lambda a: a.health_status == "At Risk" and a.escalation_notes)
    churning = _find_account(lambda a: a.health_status == "Churning")
    # An account with at least one matched ticket in the dataset, to exercise
    # the "multiple support incidents" evidence path end-to-end.
    matched_ids = {t.account_id for t in store.tickets} & {a.account_id for a in store.accounts}
    with_tickets = _find_account(lambda a: a.account_id in matched_ids)
    # A real account_id with zero linked tickets (the dominant real case).
    no_tickets = _find_account(lambda a: a.account_id not in matched_ids)
    incomplete = _find_account(lambda a: a.nps_score is None)

    cases: list[dict[str, Any]] = [
        {
            "id": "t2_healthy_account",
            "description": "Healthy account with a stable/increasing trend -- should not over-flag risk.",
            "input": {"account_id": healthy["account_id"]},
            "expected": {},
        },
        {
            "id": "t2_at_risk_account",
            "description": "At-Risk account with escalation notes -- risks must be detected and quote-grounded.",
            "input": {"account_id": at_risk["account_id"]},
            "expected": {"expect_risks_detected": True},
        },
        {
            "id": "t2_churning_account",
            "description": "Churning account -- highest-severity risk signal in the dataset.",
            "input": {"account_id": churning["account_id"]},
            "expected": {"expect_risks_detected": True},
        },
        {
            "id": "t2_account_with_matched_tickets",
            "description": "One of the few accounts with tickets that actually resolve via account_id.",
            "input": {"account_id": with_tickets["account_id"]},
            "expected": {},
        },
        {
            "id": "t2_account_zero_tickets",
            "description": "Real account with zero tickets resolving to it in the dataset -- must degrade gracefully, not fabricate ticket evidence.",
            "input": {"account_id": no_tickets["account_id"]},
            "expected": {"expect_zero_tickets": True},
        },
        {
            "id": "t2_incomplete_data_null_nps",
            "description": "Account with null nps_score and possibly other missing fields -- must not crash or invent a score.",
            "input": {"account_id": incomplete["account_id"]},
            "expected": {},
        },
        {
            "id": "t2_adversarial_unknown_account",
            "description": "Adversarial: account_id that does not exist anywhere in accounts.json.",
            "input": {"account_id": "ACC-00000"},
            "expected": {"expect_missing_account": True},
        },
    ]
    return cases
