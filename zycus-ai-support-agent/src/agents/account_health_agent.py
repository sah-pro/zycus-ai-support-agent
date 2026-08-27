"""Task 2: TAM account-health brief pipeline.

account_id -> account lookup -> 90-day ticket filter (fixed reference date)
-> LLM synthesis -> quote-grounding validation -> AccountHealthBrief.

Determinism notes:
  - temperature is fixed at 0 for both providers (see Settings).
  - the 90-day ticket window uses a caller-supplied reference date rather
    than datetime.now(), so re-running with the same reference date always
    yields the same ticket set.
  - ticket ordering is stably sorted (see DataStore.tickets_for_account).
  - every risk's `quote` field is validated to be a verbatim substring of
    its supporting ticket/account text; any quote that isn't literally
    present is dropped rather than passed through, since Task 2 explicitly
    forbids fabricated quotes.
"""
from __future__ import annotations

from datetime import datetime

from src.agents.llm_client import LLMClient, get_llm_client
from src.config.settings import settings
from src.models.account_health import AccountHealthBrief, AccountHealthMetadata, RiskFlag, TalkingPoint
from src.models.domain import Ticket
from src.services.data_loader import get_data_store
from src.utils.logging import log_operation
from src.utils.prompts import load_prompt

PROMPT_VERSION = "account_health_v1"


def _parse_reference_date(reference_date: str | None) -> datetime:
    raw = reference_date or settings.default_reference_date
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _quote_is_grounded(quote: str, ticket: Ticket | None, account_notes: list[str]) -> bool:
    if not quote:
        return False
    if ticket and (quote in ticket.subject or quote in ticket.body):
        return True
    if any(quote in note for note in account_notes):
        return True
    return False


def run_account_health(
    account_id: str,
    reference_date: str | None = None,
    llm_client: LLMClient | None = None,
) -> AccountHealthBrief:
    """Run the full account-health pipeline for one account_id."""
    client = llm_client or get_llm_client()
    store = get_data_store()
    ref_dt = _parse_reference_date(reference_date)

    with log_operation(
        "account_health",
        account_id=account_id,
        prompt_version=PROMPT_VERSION,
        model=getattr(client, "name", "unknown"),
    ) as log:
        account = store.get_account(account_id)
        tickets = store.tickets_for_account(
            account_id, reference_date=ref_dt, lookback_days=settings.account_health_lookback_days
        )
        log["account_found"] = account is not None
        log["tickets_considered"] = len(tickets)

        account_json = account.model_dump() if account else None
        tickets_json = [t.model_dump() for t in tickets]

        system_prompt, user_template = load_prompt(PROMPT_VERSION)
        user_prompt = user_template.format(
            account_id=account_id,
            reference_date=ref_dt.isoformat(),
            lookback_days=settings.account_health_lookback_days,
            ticket_count=len(tickets),
            account_json=account_json,
            tickets_json=tickets_json,
        )

        # As with Task 1: a failed call or malformed (non-dict) response
        # must degrade to a safe, guardrail-protected result, never crash
        # the pipeline or propagate an unhandled exception to the caller.
        llm_error: str | None = None
        try:
            llm_output = client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                task="account_health",
                context={
                    "account_id": account_id,
                    "account": account_json,
                    "tickets": tickets_json,
                    "lookback_days": settings.account_health_lookback_days,
                },
            )
            if not isinstance(llm_output, dict):
                raise TypeError(f"LLM client returned {type(llm_output).__name__}, expected a JSON object")
        except Exception as exc:  # noqa: BLE001 - any provider failure must degrade, never propagate
            llm_error = f"{type(exc).__name__}: {exc}"
            llm_output = {}
        log["llm_error"] = llm_error

        ticket_by_id = {t.ticket_id: t for t in tickets}
        account_notes = account.escalation_notes if account else []

        raw_risks = llm_output.get("risks") or []
        validated_risks: list[RiskFlag] = []
        dropped_risks = 0
        for r in raw_risks:
            if not isinstance(r, dict):
                dropped_risks += 1
                continue
            quote = r.get("quote", "")
            supporting_ticket = ticket_by_id.get(r.get("supporting_ticket_id", ""))
            if not _quote_is_grounded(quote, supporting_ticket, account_notes):
                # Never pass through an unverifiable quote -- drop the risk
                # rather than present unverified content as evidence. This
                # is the guardrail that catches a fabricated-quote LLM.
                dropped_risks += 1
                continue
            validated_risks.append(
                RiskFlag(
                    risk_type=r.get("risk_type", "Unspecified"),
                    severity=r.get("severity", "Medium") if r.get("severity") in ("Low", "Medium", "High", "Critical") else "Medium",
                    explanation=r.get("explanation", ""),
                    supporting_ticket_id=r.get("supporting_ticket_id", "N/A"),
                    quote=quote,
                )
            )
        log["dropped_unverified_risks"] = dropped_risks

        talking_points = [
            TalkingPoint(point=tp.get("point", ""), basis=tp.get("basis", ""))
            for tp in (llm_output.get("talking_points") or [])
            if isinstance(tp, dict) and tp.get("point")
        ]

        executive_summary = llm_output.get("executive_summary") or (
            f"Automated summary unavailable: the LLM provider {'failed' if llm_error else 'returned no summary'} "
            f"for {account_id}. Manual review recommended."
        )

        metadata = AccountHealthMetadata(
            prompt_version=PROMPT_VERSION,
            reference_date=ref_dt.isoformat(),
            lookback_days=settings.account_health_lookback_days,
            tickets_considered=len(tickets),
            account_found=account is not None,
            llm_provider=client.name,
            dropped_unverified_risks=dropped_risks,
            llm_error=llm_error,
        )

        return AccountHealthBrief(
            account_id=account_id,
            company=(account.company if account else None),
            executive_summary=executive_summary,
            risks=validated_risks,
            talking_points=talking_points,
            metadata=metadata,
        )
