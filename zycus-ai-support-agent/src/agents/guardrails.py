"""Deterministic guardrail layer applied to raw LLM output.

Design principle (per the assignment brief): the LLM decides, these
functions verify and protect. None of these functions are "smarter" than
the model -- each is a narrow, auditable check against something the
application already knows independently (a fixed enum, a deterministic
keyword signal, an actual retrieval result count). They only intervene
when the model's output conflicts with that independent ground truth, and
every intervention is returned as an explicit, loggable reason rather than
applied silently.

This module is intentionally pure / side-effect-free so it can be unit
tested against fabricated ("bad LLM") inputs without running the full
triage pipeline -- see tests/test_guardrails.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.agents.signals import DeterministicSignals
from src.models.enums import CATEGORIES, RECOMMENDED_TEAMS, URGENCIES

_URGENCY_ORDER = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}


@dataclass
class GuardrailReport:
    """Accumulates every guardrail intervention for one triage run.

    Kept separate from the final TriageResult fields so metadata can
    surface exactly what was overridden and why -- an override that
    happens silently is not meaningfully different from no guardrail at
    all.
    """

    overrides: list[str] = field(default_factory=list)

    def add(self, reason: str | None) -> None:
        if reason:
            self.overrides.append(reason)


def guard_category(raw_category: Any, report: GuardrailReport) -> str:
    """Reject any category value outside the fixed enum from DATA_SCHEMA.md."""
    if raw_category in CATEGORIES:
        return raw_category
    report.add(f"LLM returned an invalid category ({raw_category!r}); falling back to 'Bug'.")
    return "Bug"


def guard_urgency(raw_urgency: Any, signals: DeterministicSignals, report: GuardrailReport) -> str:
    """Validate urgency enum membership, then enforce the deterministic floor.

    A ticket containing unambiguous outage/critical language (see
    ``src.models.enums.URGENCY_KEYWORDS``) sets an urgency floor the model
    is not allowed to go below without an explicit, logged override. This
    is what stops a misbehaving or adversarial model from silently
    downgrading a clear P1 to a low-priority ticket.
    """
    urgency = raw_urgency if raw_urgency in URGENCIES else None
    if urgency is None:
        fallback = signals.suggested_urgency_floor or "P3"
        report.add(f"LLM returned an invalid/missing urgency ({raw_urgency!r}); falling back to {fallback!r}.")
        urgency = fallback

    floor = signals.suggested_urgency_floor
    if floor and _URGENCY_ORDER[urgency] > _URGENCY_ORDER[floor]:
        report.add(
            f"LLM urgency {urgency!r} was below the deterministic floor {floor!r} implied by "
            f"detected signals {signals.urgency_keyword_hits}; overridden to protect against under-triage."
        )
        urgency = floor

    return urgency


def guard_known_issue(raw_known_issue: Any, strong_match_count: int, report: GuardrailReport) -> bool:
    """Never allow ``known_issue=True`` unless retrieval found a genuinely strong match.

    Prevents the model from claiming a documented/known issue exists when
    no knowledge-base evidence -- or only weak, incidental term overlap --
    was actually retrieved for this ticket. `strong_match_count` must
    already be filtered to results at/above `settings.min_kb_relevance_score`;
    a nonzero *total* retrieval count is not sufficient, since the BM25
    index can return low-score "matches" on nothing more than common words.
    """
    claimed = bool(raw_known_issue)
    if claimed and strong_match_count == 0:
        report.add(
            "LLM claimed known_issue=True but retrieval returned no knowledge-base match at or "
            "above the minimum relevance threshold; overridden to False (no fabricated KB claims)."
        )
        return False
    return claimed


def guard_recommended_team(raw_team: Any, report: GuardrailReport, fallback: str = "Tier-1 Support") -> str:
    if raw_team in RECOMMENDED_TEAMS:
        return raw_team
    report.add(f"LLM returned an unknown team ({raw_team!r}); falling back to {fallback!r}.")
    return fallback


def guard_product(raw_product: Any, valid_products: list[str], report: GuardrailReport) -> str:
    if raw_product in valid_products or raw_product == "Unknown":
        return raw_product
    report.add(f"LLM returned a product not in the fixed catalog ({raw_product!r}); overridden to 'Unknown'.")
    return "Unknown"


__all__ = [
    "GuardrailReport",
    "guard_category",
    "guard_urgency",
    "guard_known_issue",
    "guard_recommended_team",
    "guard_product",
    "URGENCIES",
]
