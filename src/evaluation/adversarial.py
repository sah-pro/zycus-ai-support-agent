"""A deliberately misbehaving LLM client, used only by the evaluation
harness and tests to prove the deterministic guardrail layer actually
catches bad model output.

Per the assignment brief: "Create a fake/mocked LLM implementation that
deliberately produces bad outputs ... The system must detect the conflict
and produce the correct guarded result." This is that fake implementation.

`ScriptedBadLLMClient` is never selected by `get_llm_client()` and is not
reachable through any environment variable -- it is only ever constructed
directly by the evaluation harness or tests and passed to `run_triage` /
`run_account_health` via their `llm_client=` parameter.
"""
from __future__ import annotations

from typing import Any

from src.agents.llm_client import LLMClient


class ScriptedBadLLMClient(LLMClient):
    """Returns a fixed, caller-supplied response (or raises) regardless of input.

    Three failure modes, matching how a real provider can actually fail:
      - `response`: return this dict verbatim, however wrong its contents.
      - `raise_exc`: raise this exception, simulating a network/parsing failure.
      - `return_non_dict`: return this value instead of a dict, simulating a
        provider that responded with something that isn't valid structured output.
    """

    name = "adversarial-scripted"

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        raise_exc: Exception | None = None,
        return_non_dict: Any = None,
    ) -> None:
        if sum(x is not None for x in (response, raise_exc, return_non_dict)) != 1:
            raise ValueError("Specify exactly one of response, raise_exc, return_non_dict.")
        self._response = response
        self._raise_exc = raise_exc
        self._return_non_dict = return_non_dict

    def complete_json(self, system_prompt: str, user_prompt: str, task: str, context: dict[str, Any]) -> Any:
        if self._raise_exc is not None:
            raise self._raise_exc
        if self._return_non_dict is not None:
            return self._return_non_dict
        return self._response


# ---------------------------------------------------------------------------
# Named adversarial scenarios, reused by both the eval harness and unit tests
# so the two never drift apart.
# ---------------------------------------------------------------------------

_VALID_TRIAGE_SHAPE = {
    "product": "DataBridge Pro",
    "product_area": "Connectors",
    "category": "Bug",
    "reasoning": "Scripted adversarial response for guardrail testing.",
    "confidence": 0.9,
    "recommended_team": "Tier-1 Support",
    "routing_reasoning": "Scripted.",
    "draft_response": "Scripted draft response.",
}


def urgency_downgrade_client() -> ScriptedBadLLMClient:
    """LLM incorrectly downgrades an obvious P1 outage to P4."""
    return ScriptedBadLLMClient(response={**_VALID_TRIAGE_SHAPE, "urgency": "P4", "known_issue": False})


def invalid_category_client() -> ScriptedBadLLMClient:
    """LLM invents a category that isn't in the fixed enum."""
    return ScriptedBadLLMClient(
        response={**_VALID_TRIAGE_SHAPE, "category": "Cosmic Anomaly", "urgency": "P3", "known_issue": False}
    )


def invalid_urgency_client() -> ScriptedBadLLMClient:
    """LLM returns an urgency value outside P1-P4."""
    return ScriptedBadLLMClient(response={**_VALID_TRIAGE_SHAPE, "urgency": "P9-CRITICAL", "known_issue": False})


def hallucinated_kb_client() -> ScriptedBadLLMClient:
    """LLM claims a known KB match exists when retrieval found nothing."""
    return ScriptedBadLLMClient(
        response={**_VALID_TRIAGE_SHAPE, "urgency": "P3", "known_issue": True}
    )


def malformed_json_client() -> ScriptedBadLLMClient:
    """Simulates a provider response that fails JSON parsing entirely."""
    return ScriptedBadLLMClient(raise_exc=ValueError("Expecting value: line 1 column 1 (char 0)"))


def missing_fields_client() -> ScriptedBadLLMClient:
    """LLM returns a technically-valid but essentially empty JSON object."""
    return ScriptedBadLLMClient(response={})


def non_dict_response_client() -> ScriptedBadLLMClient:
    """Simulates a provider that returned a JSON array/string instead of an object."""
    return ScriptedBadLLMClient(return_non_dict=["not", "a", "dict"])


def fabricated_quote_client() -> ScriptedBadLLMClient:
    """Task 2: LLM invents a risk with a quote that is not a substring of any real ticket/note."""
    return ScriptedBadLLMClient(
        response={
            "executive_summary": "Scripted adversarial account-health summary.",
            "risks": [
                {
                    "risk_type": "Escalation note",
                    "severity": "Critical",
                    "explanation": "Fabricated for testing.",
                    "supporting_ticket_id": "DOES-NOT-EXIST",
                    "quote": "The CEO personally threatened to sue us over this outage.",
                }
            ],
            "talking_points": [{"point": "Scripted talking point.", "basis": "Scripted."}],
        }
    )


def invalid_severity_client() -> ScriptedBadLLMClient:
    """Task 2: LLM returns a severity value outside the fixed enum."""
    return ScriptedBadLLMClient(
        response={
            "executive_summary": "Scripted adversarial account-health summary.",
            "risks": [
                {
                    "risk_type": "Escalation note",
                    "severity": "APOCALYPTIC",
                    "explanation": "Scripted.",
                    "supporting_ticket_id": "N/A",
                    "quote": "",
                }
            ],
            "talking_points": [],
        }
    )


ADVERSARIAL_TASK1_SCENARIOS: dict[str, Any] = {
    "urgency_downgrade": urgency_downgrade_client,
    "invalid_category": invalid_category_client,
    "invalid_urgency": invalid_urgency_client,
    "hallucinated_kb": hallucinated_kb_client,
    "malformed_json": malformed_json_client,
    "missing_fields": missing_fields_client,
    "non_dict_response": non_dict_response_client,
}

ADVERSARIAL_TASK2_SCENARIOS: dict[str, Any] = {
    "fabricated_quote": fabricated_quote_client,
    "malformed_json": malformed_json_client,
    "missing_fields": missing_fields_client,
}
