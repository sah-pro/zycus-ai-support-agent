"""Scoring primitives for the evaluation harness (Task 3).

Design principle from the assignment brief: "do not use an LLM judge for
something that can be evaluated deterministically." Every score component
below is rule-based / exact-match / schema-based. The only place an LLM
judge would plausibly add value -- subjective tone/quality of the drafted
response text -- is scored with a cheap heuristic rubric instead, documented
as a known limitation in DESIGN.md, so the harness has zero LLM-judge cost
and zero non-determinism.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.models.account_health import AccountHealthBrief
from src.models.triage import TriageResult


@dataclass
class ScoreBreakdown:
    components: dict[str, float] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)

    @property
    def total(self) -> float:
        if not self.weights:
            return 0.0
        return round(sum(self.components[k] * self.weights[k] for k in self.weights), 4)


# ---------------------------------------------------------------------------
# Task 1 scoring
# ---------------------------------------------------------------------------

# Weights chosen to mirror marks weighting in the assignment brief itself
# (classification/routing/prioritisation is the whole point of Task 1), with
# schema validity as a hard gate (a broken contract makes everything else
# moot) and response quality weighted lowest since it is the most subjective
# component and the assignment explicitly deprioritizes LLM-judge usage.
TASK1_WEIGHTS = {
    "schema_validity": 0.20,
    "urgency_accuracy": 0.25,
    "category_accuracy": 0.20,
    "retrieval_quality": 0.15,
    "routing_quality": 0.10,
    "response_quality": 0.10,
}


def score_task1(result: TriageResult, expected: dict[str, Any]) -> ScoreBreakdown:
    components: dict[str, float] = {}

    # Schema validity: if we have a TriageResult object at all, pydantic has
    # already validated it. This component checks the *stricter* app-level
    # invariants that pydantic's base types don't (e.g. non-empty reasoning).
    components["schema_validity"] = 1.0 if result.classification.reasoning.strip() else 0.5

    expected_urgency = expected.get("expected_urgency")
    if expected_urgency:
        if result.classification.urgency == expected_urgency:
            components["urgency_accuracy"] = 1.0
        elif expected.get("acceptable_urgencies") and result.classification.urgency in expected["acceptable_urgencies"]:
            components["urgency_accuracy"] = 0.7
        else:
            components["urgency_accuracy"] = 0.0
    else:
        components["urgency_accuracy"] = 1.0  # no expectation set -- do not penalize

    expected_category = expected.get("expected_category")
    if expected_category:
        components["category_accuracy"] = 1.0 if result.classification.category == expected_category else 0.0
    else:
        components["category_accuracy"] = 1.0

    expect_kb_match = expected.get("expect_known_issue")
    if expect_kb_match is not None:
        components["retrieval_quality"] = 1.0 if bool(result.knowledge_base.known_issue) == bool(expect_kb_match) else 0.3
    else:
        components["retrieval_quality"] = 1.0 if result.knowledge_base.matches else 0.5

    expected_team = expected.get("expected_team")
    if expected_team:
        components["routing_quality"] = 1.0 if result.routing.recommended_team == expected_team else 0.3
    else:
        components["routing_quality"] = 1.0 if result.routing.recommended_team else 0.0

    draft = result.response.draft.strip()
    response_quality = 0.0
    if draft:
        response_quality += 0.5
    if len(draft) > 40:
        response_quality += 0.3
    if "thank" in draft.lower() or "sorry" in draft.lower() or "look" in draft.lower():
        response_quality += 0.2
    components["response_quality"] = min(response_quality, 1.0)

    return ScoreBreakdown(components=components, weights=TASK1_WEIGHTS)


# ---------------------------------------------------------------------------
# Task 2 scoring
# ---------------------------------------------------------------------------

TASK2_WEIGHTS = {
    "required_sections_present": 0.20,
    "quote_grounding": 0.30,
    "risk_detection": 0.20,
    "recommendation_quality": 0.15,
    "graceful_missing_data": 0.15,
}


def _quotes_are_grounded(brief: AccountHealthBrief, ticket_bodies: dict[str, str], account_notes: list[str]) -> float:
    if not brief.risks:
        return 1.0  # nothing to check; not a failure by itself
    grounded = 0
    for r in brief.risks:
        haystacks = []
        if r.supporting_ticket_id in ticket_bodies:
            haystacks.append(ticket_bodies[r.supporting_ticket_id])
        haystacks.extend(account_notes)
        if any(r.quote in h for h in haystacks):
            grounded += 1
    return grounded / len(brief.risks)


def score_task2(
    brief: AccountHealthBrief,
    expected: dict[str, Any],
    ticket_bodies: dict[str, str],
    account_notes: list[str],
) -> ScoreBreakdown:
    components: dict[str, float] = {}

    components["required_sections_present"] = (
        1.0
        if brief.executive_summary.strip() and brief.talking_points
        else (0.5 if brief.executive_summary.strip() else 0.0)
    )

    components["quote_grounding"] = _quotes_are_grounded(brief, ticket_bodies, account_notes)

    expect_risks = expected.get("expect_risks_detected")
    if expect_risks is not None:
        components["risk_detection"] = 1.0 if bool(brief.risks) == bool(expect_risks) else 0.0
    else:
        components["risk_detection"] = 1.0

    components["recommendation_quality"] = 1.0 if any(tp.point.strip() for tp in brief.talking_points) else 0.0

    expect_graceful = expected.get("expect_missing_account") or expected.get("expect_zero_tickets")
    if expect_graceful:
        handled = (not brief.metadata.account_found or brief.metadata.tickets_considered == 0) and bool(
            brief.executive_summary.strip()
        )
        components["graceful_missing_data"] = 1.0 if handled else 0.0
    else:
        components["graceful_missing_data"] = 1.0

    return ScoreBreakdown(components=components, weights=TASK2_WEIGHTS)


PASS_THRESHOLD = 0.6
