"""Structured output contract for the TAM account-health brief (Task 2)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class RiskFlag(BaseModel):
    risk_type: str
    severity: Literal["Low", "Medium", "High", "Critical"]
    explanation: str
    supporting_ticket_id: str
    quote: str = Field(description="Verbatim substring copied from the ticket subject/body. Never fabricated.")


class TalkingPoint(BaseModel):
    point: str
    basis: str = Field(description="What evidence (ticket id / account field) this point is grounded in.")


class AccountHealthMetadata(BaseModel):
    prompt_version: str
    reference_date: str
    lookback_days: int
    tickets_considered: int
    account_found: bool
    llm_provider: str
    dropped_unverified_risks: int = Field(
        default=0,
        description="Number of LLM-proposed risks discarded because their quote could not be "
        "verified as a verbatim substring of the source ticket/account text.",
    )
    llm_error: str | None = Field(
        default=None,
        description="Set when the LLM call failed or returned malformed output; the pipeline "
        "still produced a safe, guardrail-protected result instead of crashing.",
    )


class AccountHealthBrief(BaseModel):
    """The final, validated Task 2 output contract."""

    account_id: str
    company: Optional[str] = None
    executive_summary: str
    risks: list[RiskFlag] = []
    talking_points: list[TalkingPoint] = []
    metadata: AccountHealthMetadata
