"""Task 1: intelligent ticket triage pipeline.

Pipeline:
  raw ticket -> normalization -> deterministic signal extraction
  -> KB retrieval -> LLM reasoning/classification -> schema validation
  -> post-processing -> TriageResult
"""
from __future__ import annotations

from src.agents.guardrails import (
    GuardrailReport,
    guard_category,
    guard_known_issue,
    guard_product,
    guard_recommended_team,
    guard_urgency,
)
from src.agents.llm_client import LLMClient, get_llm_client
from src.agents.signals import extract_signals
from src.config.settings import settings
from src.models.enums import PRODUCTS
from src.models.triage import (
    Classification,
    DraftResponse,
    KBMatch,
    KnowledgeBaseResult,
    Routing,
    TicketInput,
    TriageMetadata,
    TriageResult,
)
from src.retrieval.index import retrieve
from src.utils.logging import log_operation
from src.utils.prompts import load_prompt

PROMPT_VERSION = "triage_v1"


def _normalize(subject: str, body: str) -> tuple[str, str]:
    return subject.strip(), body.strip()


def _guess_product(text: str) -> str | None:
    lower = text.lower()
    for product in PRODUCTS:
        if product.lower() in lower:
            return product
    return None


def run_triage(
    ticket_input: TicketInput,
    llm_client: LLMClient | None = None,
) -> TriageResult:
    """Run the full triage pipeline for one ticket and return a validated result."""
    client = llm_client or get_llm_client()

    with log_operation(
        "triage",
        ticket_id=ticket_input.ticket_id or "unassigned",
        prompt_version=PROMPT_VERSION,
        model=getattr(client, "name", "unknown"),
    ) as log:
        subject, body = _normalize(ticket_input.subject, ticket_input.body)

        # 1. Deterministic signal extraction
        signals = extract_signals(subject, body)

        # 2. Knowledge-base retrieval
        query = f"{subject} {body}"
        results = retrieve(query, top_k=settings.retrieval_top_k)
        kb_matches_ctx = [
            {
                "document": r.chunk.document,
                "section": r.chunk.section,
                "score": r.score,
                "reason": r.reason,
            }
            for r in results
        ]
        log["retrieval_count"] = len(results)

        # 3. LLM reasoning/classification (mock or real, same interface)
        system_prompt, user_template = load_prompt(PROMPT_VERSION)
        user_prompt = user_template.format(
            subject=subject,
            body=body,
            signals="\n".join(signals.as_prompt_lines()) or "None detected.",
            retrieval_count=len(results),
            kb_context="\n".join(
                f"- {m['document']} :: {m['section']} (score={m['score']}) -- {m['reason']}"
                for m in kb_matches_ctx
            )
            or "No relevant knowledge-base sections were found.",
        )
        # LLM output is never trusted directly: a failed call, a malformed
        # (non-dict) response, or an exception raised by the provider must
        # degrade to a safe, guardrail-protected result rather than crash
        # the pipeline. `llm_output = {}` lets every `.get()` below fall
        # through to its deterministic default.
        llm_error: str | None = None
        try:
            llm_output = client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                task="triage",
                context={
                    "subject": subject,
                    "body": body,
                    "signals": {
                        "error_codes": signals.error_codes,
                        "urgency_keyword_hits": signals.urgency_keyword_hits,
                        "suggested_urgency_floor": signals.suggested_urgency_floor,
                    },
                    "kb_matches": kb_matches_ctx,
                    "guessed_product": _guess_product(query),
                },
            )
            if not isinstance(llm_output, dict):
                raise TypeError(f"LLM client returned {type(llm_output).__name__}, expected a JSON object")
        except Exception as exc:  # noqa: BLE001 - any provider failure must degrade, never propagate
            llm_error = f"{type(exc).__name__}: {exc}"
            llm_output = {}
        log["llm_error"] = llm_error

        # 4. Deterministic guardrails -- the LLM decides, these verify and protect.
        report = GuardrailReport()
        category = guard_category(llm_output.get("category"), report)
        urgency = guard_urgency(llm_output.get("urgency"), signals, report)
        strong_match_count = sum(1 for r in results if r.score >= settings.min_kb_relevance_score)
        known_issue = guard_known_issue(llm_output.get("known_issue", False), strong_match_count, report)
        recommended_team = guard_recommended_team(llm_output.get("recommended_team"), report)
        product = guard_product(llm_output.get("product") or "Unknown", PRODUCTS, report)
        log["guardrail_overrides"] = len(report.overrides)

        try:
            confidence = float(llm_output.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
            report.add(f"LLM returned a non-numeric confidence ({llm_output.get('confidence')!r}); defaulted to 0.5.")
        confidence = min(max(confidence, 0.0), 1.0)

        classification = Classification(
            product=product,
            product_area=llm_output.get("product_area") or "General",
            category=category,
            urgency=urgency,
            reasoning=llm_output.get("reasoning", ""),
            confidence=confidence,
        )

        kb_result = KnowledgeBaseResult(
            known_issue=known_issue,
            matches=[
                KBMatch(document=m["document"], section=m["section"], relevance_score=m["score"], reason=m["reason"])
                for m in kb_matches_ctx
            ],
        )

        routing = Routing(
            recommended_team=recommended_team,
            reasoning=llm_output.get("routing_reasoning", ""),
        )

        response = DraftResponse(draft=llm_output.get("draft_response") or "Thanks for reaching out -- we're looking into this.")

        metadata = TriageMetadata(
            prompt_version=PROMPT_VERSION,
            retrieval_count=len(results),
            llm_provider=client.name,
            deterministic_signals=signals.as_prompt_lines(),
            guardrail_overrides=report.overrides,
            llm_error=llm_error,
        )

        return TriageResult(
            ticket=ticket_input,
            classification=classification,
            knowledge_base=kb_result,
            routing=routing,
            response=response,
            metadata=metadata,
        )
