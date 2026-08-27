"""Deterministic, rule-based signal extraction run before the LLM sees a ticket.

Per the assignment brief: "do not blindly ask the LLM to invent everything ...
use deterministic logic where it improves reliability." These signals are
passed into the LLM prompt as grounded hints, and are also asserted on
directly in the evaluation harness (Task 3) since they require no LLM judge.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.models.enums import KNOWN_ERROR_CODE_PATTERN, URGENCY_KEYWORDS

_ERROR_CODE_RE = re.compile(KNOWN_ERROR_CODE_PATTERN)


@dataclass
class DeterministicSignals:
    error_codes: list[str] = field(default_factory=list)
    urgency_keyword_hits: dict[str, list[str]] = field(default_factory=dict)
    suggested_urgency_floor: str | None = None
    is_empty_ticket: bool = False

    def as_prompt_lines(self) -> list[str]:
        lines = []
        if self.error_codes:
            lines.append(f"Detected error code(s) in ticket text: {', '.join(self.error_codes)}")
        for tier, hits in self.urgency_keyword_hits.items():
            lines.append(f"Urgency-{tier} language detected: {', '.join(hits)}")
        return lines


def extract_signals(subject: str, body: str) -> DeterministicSignals:
    """Run cheap, deterministic pattern checks over raw ticket text."""
    full_text = f"{subject}\n{body}"
    lower = full_text.lower()

    error_codes = sorted(set(_ERROR_CODE_RE.findall(full_text)))

    urgency_hits: dict[str, list[str]] = {}
    for tier, keywords in URGENCY_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in lower]
        if hits:
            urgency_hits[tier] = hits

    suggested_floor = None
    if "P1" in urgency_hits:
        suggested_floor = "P1"
    elif "P2" in urgency_hits:
        suggested_floor = "P2"

    return DeterministicSignals(
        error_codes=error_codes,
        urgency_keyword_hits=urgency_hits,
        suggested_urgency_floor=suggested_floor,
        is_empty_ticket=not body.strip(),
    )
