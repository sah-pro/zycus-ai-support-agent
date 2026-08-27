"""FastAPI service exposing the Task 1 and Task 2 pipelines.

Run locally with:
    uvicorn src.api.main:app --reload
"""
from __future__ import annotations

import re

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError

from src.agents.account_health_agent import run_account_health
from src.agents.triage_agent import run_triage
from src.config.settings import settings
from src.models.account_health import AccountHealthBrief
from src.models.triage import TicketInput, TriageResult

app = FastAPI(
    title="Zycus AI Support",
    description="Ticket triage and TAM account-health brief service.",
    version="0.1.0",
)

_ACCOUNT_ID_RE = re.compile(r"^ACC-\d+$")


class AccountHealthRequest(BaseModel):
    account_id: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_provider": settings.llm_provider}


@app.post("/triage", response_model=TriageResult)
def triage(payload: TicketInput) -> TriageResult:
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="Ticket body must not be empty.")
    try:
        return run_triage(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise HTTPException(status_code=500, detail="Internal error during triage.") from exc


@app.post("/account-health", response_model=AccountHealthBrief)
def account_health(payload: AccountHealthRequest) -> AccountHealthBrief:
    # Validate account_id shape before touching any lookup logic -- this is
    # user-controlled input and must not be used to probe the filesystem or
    # any other resource.
    if not _ACCOUNT_ID_RE.match(payload.account_id):
        raise HTTPException(status_code=400, detail="account_id must match pattern 'ACC-<digits>'.")
    try:
        brief = run_account_health(payload.account_id)
    except Exception as exc:  # pragma: no cover - defensive boundary
        raise HTTPException(status_code=500, detail="Internal error during account-health synthesis.") from exc
    if not brief.metadata.account_found and brief.metadata.tickets_considered == 0:
        raise HTTPException(status_code=404, detail=f"No account or ticket data found for {payload.account_id}.")
    return brief
