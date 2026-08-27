"""Guardrail ('bad LLM') evaluation cases for Task 3.

Unlike the cases in cases_task1.py / cases_task2.py, which exercise the
*default* mock provider end-to-end, every case here injects a deliberately
misbehaving LLM client (src/evaluation/adversarial.py) via
`llm_client_factory` and asserts the deterministic guardrail layer -- not
the model -- produced the correct final result. This is the harness-level
demonstration the assignment brief asks for: "The system must detect the
conflict and produce the correct guarded result."
"""
from __future__ import annotations

from typing import Any

from src.evaluation.adversarial import (
    fabricated_quote_client,
    hallucinated_kb_client,
    invalid_category_client,
    invalid_urgency_client,
    malformed_json_client,
    missing_fields_client,
    urgency_downgrade_client,
)
from src.services.data_loader import get_data_store


def build_task1_guardrail_cases() -> list[dict[str, Any]]:
    return [
        {
            "id": "g1_bad_llm_p1_downgrade_rejected",
            "description": (
                "BAD LLM TEST (assignment example): a clearly critical production outage "
                "must not end up P4 just because a misbehaving LLM said so."
            ),
            "input": {
                "subject": "Production system is completely down",
                "body": "Production system is completely down. All users are unable to access the service.",
                "ticket_id": "EVAL-ADV-P1",
            },
            "llm_client_factory": urgency_downgrade_client,
            "expected": {"expected_urgency": "P1"},
        },
        {
            "id": "g1_bad_llm_invalid_category_rejected",
            "description": "LLM invents a category outside the fixed enum; guardrail must fall back to 'Bug'.",
            "input": {
                "subject": "Export formatting looks off",
                "body": "Our CSV export sometimes wraps long text fields differently than expected.",
                "ticket_id": "EVAL-ADV-CAT",
            },
            "llm_client_factory": invalid_category_client,
            "expected": {"expected_category": "Bug"},
        },
        {
            "id": "g1_bad_llm_invalid_urgency_rejected",
            "description": "LLM returns a value outside P1-P4; guardrail must fall back to a valid enum member.",
            "input": {
                "subject": "General question",
                "body": "Just checking on a minor UI detail, nothing urgent.",
                "ticket_id": "EVAL-ADV-URG",
            },
            "llm_client_factory": invalid_urgency_client,
            "expected": {},
        },
        {
            "id": "g1_bad_llm_hallucinated_kb_rejected",
            "description": (
                "LLM claims known_issue=True for a ticket with no real knowledge-base match; "
                "guardrail must clear the claim since retrieval found nothing at/above the "
                "relevance threshold."
            ),
            "input": {
                "subject": "Unrelated topic",
                "body": "The giraffe rode a bicycle past the lighthouse while eating a pumpkin and humming a symphony near the glacier.",
                "ticket_id": "EVAL-ADV-KB",
            },
            "llm_client_factory": hallucinated_kb_client,
            "expected": {"expect_known_issue": False},
        },
        {
            "id": "g1_bad_llm_malformed_json_degrades",
            "description": "Provider call raises instead of returning JSON; pipeline must still floor urgency correctly, not crash.",
            "input": {
                "subject": "Production system is completely down",
                "body": "Production system is completely down. All users are unable to access the service.",
                "ticket_id": "EVAL-ADV-MALFORMED",
            },
            "llm_client_factory": malformed_json_client,
            "expected": {"expected_urgency": "P1"},
        },
        {
            "id": "g1_bad_llm_missing_fields_degrades",
            "description": "Provider returns an empty JSON object; pipeline must fall back to safe defaults, not crash.",
            "input": {
                "subject": "General question",
                "body": "Just checking on a minor UI detail, nothing urgent.",
                "ticket_id": "EVAL-ADV-EMPTY",
            },
            "llm_client_factory": missing_fields_client,
            "expected": {"expected_category": "Bug"},
        },
    ]


def build_task2_guardrail_cases() -> list[dict[str, Any]]:
    store = get_data_store()
    any_account_id = store.accounts[0].account_id

    return [
        {
            "id": "g2_bad_llm_fabricated_quote_rejected",
            "description": "LLM invents a risk with a quote that is not a verbatim substring of any real ticket/note; must be dropped.",
            "input": {"account_id": any_account_id},
            "llm_client_factory": fabricated_quote_client,
            "expected": {"expect_risks_detected": False},
        },
        {
            "id": "g2_bad_llm_malformed_json_degrades",
            "description": "Provider call raises instead of returning JSON; pipeline must still return a valid, non-crashing brief.",
            "input": {"account_id": any_account_id},
            "llm_client_factory": malformed_json_client,
            "expected": {},
        },
        {
            "id": "g2_bad_llm_missing_fields_degrades",
            "description": "Provider returns an empty JSON object; pipeline must degrade to a safe, structurally valid brief.",
            "input": {"account_id": any_account_id},
            "llm_client_factory": missing_fields_client,
            "expected": {},
        },
    ]


def build_guardrail_cases() -> dict[str, list[dict[str, Any]]]:
    return {
        "task1": build_task1_guardrail_cases(),
        "task2": build_task2_guardrail_cases(),
    }
