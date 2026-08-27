"""Structured output contract for the ticket-triage pipeline (Task 1)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from src.models.enums import CATEGORIES, PRODUCTS, RECOMMENDED_TEAMS, URGENCIES


class TicketInput(BaseModel):
    """Raw input accepted by the triage pipeline."""

    subject: str = Field(default="", max_length=500)
    body: str = Field(min_length=1, max_length=20_000)
    ticket_id: Optional[str] = None


class KBMatch(BaseModel):
    document: str
    section: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str


class Classification(BaseModel):
    product: str
    product_area: str
    category: Literal[
        "Bug", "Feature Request", "How-To", "Performance",
        "Billing", "Integration", "Onboarding", "Data Loss",
    ]
    urgency: Literal["P1", "P2", "P3", "P4"]
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)

    @field_validator("product")
    @classmethod
    def _product_must_be_known_or_flagged(cls, v: str) -> str:
        if v not in PRODUCTS and v != "Unknown":
            # Do not silently coerce -- surface the anomaly instead of hiding it.
            return "Unknown"
        return v


class KnowledgeBaseResult(BaseModel):
    known_issue: bool
    matches: list[KBMatch] = []


class Routing(BaseModel):
    recommended_team: str
    reasoning: str

    @field_validator("recommended_team")
    @classmethod
    def _team_must_be_known(cls, v: str) -> str:
        return v if v in RECOMMENDED_TEAMS else "Tier-1 Support"


class DraftResponse(BaseModel):
    draft: str


class TriageMetadata(BaseModel):
    prompt_version: str
    retrieval_count: int
    llm_provider: str
    deterministic_signals: list[str] = Field(
        default_factory=list,
        description="Rule-based signals detected before the LLM ran (error codes, urgency keywords, etc.)",
    )
    guardrail_overrides: list[str] = Field(
        default_factory=list,
        description=(
            "Every deterministic guardrail intervention applied to this result, e.g. an "
            "urgency downgrade that was rejected or a hallucinated KB claim that was cleared. "
            "Empty when the LLM output needed no correction."
        ),
    )
    llm_error: str | None = Field(
        default=None,
        description="Set when the LLM call failed or returned malformed output; the pipeline "
        "still produced a safe, guardrail-protected result instead of crashing.",
    )


class TriageResult(BaseModel):
    """The final, validated Task 1 output contract."""

    ticket: TicketInput
    classification: Classification
    knowledge_base: KnowledgeBaseResult
    routing: Routing
    response: DraftResponse
    metadata: TriageMetadata
