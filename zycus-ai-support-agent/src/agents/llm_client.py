"""LLM provider abstraction.

Two implementations:
  - MockLLMClient: fully deterministic, offline, no network, no API key.
    This is the DEFAULT provider. It runs a small set of rule-based
    templates driven by the same structured context (ticket signals,
    retrieved KB chunks, account/ticket evidence) that a real LLM would
    receive, so the rest of the pipeline (validation, evaluation, API,
    CLI) can be built and tested identically regardless of provider.
  - AnthropicLLMClient: calls the real Anthropic Messages API. Only
    instantiated when LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY is set.

Callers depend only on the `LLMClient` interface, never on a concrete
implementation, so switching providers is a one-line config change.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from src.config.settings import settings


class LLMClient(ABC):
    """Common interface both providers implement."""

    name: str

    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str, task: str, context: dict[str, Any]) -> dict:
        """Return a parsed JSON dict for the given prompt.

        `task` identifies which mock template to use ("triage" or
        "account_health") and is ignored by the real Anthropic client,
        which relies entirely on the prompt text.
        `context` carries the structured, deterministic inputs (retrieved
        KB chunks, ticket signals, account/ticket evidence) so the mock
        client can produce a grounded, non-hallucinated response without
        calling out to a network.
        """
        raise NotImplementedError


class MockLLMClient(LLMClient):
    """Deterministic offline stand-in for a real LLM.

    Templates are simple and rule-driven, but they consume the *same*
    grounded context (KB matches, ticket signals, evidence quotes) a real
    model would be given, and produce output through the same schema
    validation path -- so this is a faithful stand-in for pipeline testing,
    not a rubber stamp.
    """

    name = "mock"

    def complete_json(self, system_prompt: str, user_prompt: str, task: str, context: dict[str, Any]) -> dict:
        if task == "triage":
            return self._triage(context)
        if task == "account_health":
            return self._account_health(context)
        raise ValueError(f"Unknown mock task: {task}")

    # -- Task 1 -----------------------------------------------------------
    def _triage(self, context: dict[str, Any]) -> dict:
        signals = context["signals"]
        kb_matches = context["kb_matches"]
        subject = context["subject"]
        body = context["body"]
        text = f"{subject} {body}".lower()

        product = context.get("guessed_product") or "Unknown"
        product_area = context.get("guessed_product_area") or (
            kb_matches[0]["section"] if kb_matches else "General"
        )

        category = self._guess_category(text)
        urgency = signals.get("suggested_urgency_floor") or self._guess_urgency(text)

        reasoning_parts = [f"Ticket text matched category signals for '{category}'."]
        if signals.get("error_codes"):
            reasoning_parts.append(f"Detected known error code(s): {', '.join(signals['error_codes'])}.")
        if signals.get("urgency_keyword_hits"):
            reasoning_parts.append(f"Urgency language detected: {signals['urgency_keyword_hits']}.")
        if kb_matches:
            reasoning_parts.append(
                f"Closest knowledge-base match: {kb_matches[0]['document']} ({kb_matches[0]['section']})."
            )
        else:
            reasoning_parts.append("No strong knowledge-base match found; treating as a novel issue.")

        known_issue = bool(kb_matches) and (bool(signals.get("error_codes")) or kb_matches[0]["score"] > 0.35)

        team = self._route(category, urgency)

        draft = self._draft_response(subject, category, urgency, kb_matches, signals)

        return {
            "product": product,
            "product_area": product_area,
            "category": category,
            "urgency": urgency,
            "reasoning": " ".join(reasoning_parts),
            "confidence": 0.6 if product != "Unknown" else 0.3,
            "known_issue": known_issue,
            "recommended_team": team,
            "routing_reasoning": f"Routed to {team} based on category '{category}' and urgency '{urgency}'.",
            "draft_response": draft,
        }

    @staticmethod
    def _guess_category(text: str) -> str:
        checks = [
            ("Data Loss", ["data loss", "missing data", "corrupted", "disappeared", "lost records"]),
            ("Billing", ["invoice", "billing", "charge", "payment", "seats licensed", "plan upgrade", "renewal"]),
            ("Integration", ["integration", "connector", "webhook", "third-party", "oauth"]),
            ("Performance", ["slow", "timeout", "latency", "throughput", "performance", "lag"]),
            ("Feature Request", ["would like", "feature request", "expected behaviour", "please add", "request:"]),
            ("Onboarding", ["onboarding", "new organisation", "getting started", "setup"]),
            ("How-To", ["how do i", "how to", "documentation", "guidance"]),
        ]
        for category, kws in checks:
            if any(kw in text for kw in kws):
                return category
        return "Bug"

    @staticmethod
    def _guess_urgency(text: str) -> str:
        if any(kw in text for kw in ["all users", "production down", "cannot access any", "business stopped"]):
            return "P1"
        if any(kw in text for kw in ["urgent", "critical", "blocking", "major impact"]):
            return "P2"
        if any(kw in text for kw in ["minor", "cosmetic", "small issue", "when convenient"]):
            return "P4"
        return "P3"

    @staticmethod
    def _route(category: str, urgency: str) -> str:
        if category == "Billing":
            return "Billing & Accounts"
        if category == "Onboarding":
            return "Onboarding & Customer Success"
        if category in ("Bug", "Data Loss", "Performance") and urgency in ("P1", "P2"):
            return "Tier-2 Support"
        if category == "Feature Request":
            return "Product Engineering"
        return "Tier-1 Support"

    @staticmethod
    def _draft_response(subject: str, category: str, urgency: str, kb_matches: list[dict], signals: dict) -> str:
        opening = "Thanks for reaching out, and sorry for the disruption this is causing." if urgency in ("P1", "P2") else "Thanks for reaching out."
        kb_line = ""
        if kb_matches:
            kb_line = (
                f" I found a related reference in our knowledge base "
                f"({kb_matches[0]['document']}, section '{kb_matches[0]['section']}') "
                "that may help while we investigate further."
            )
        code_line = ""
        if signals.get("error_codes"):
            code_line = f" I can see the error code {signals['error_codes'][0]} in your report, which helps narrow down the cause."
        closing = (
            "We're prioritizing this given the reported impact and will follow up shortly with next steps."
            if urgency in ("P1", "P2")
            else "We'll look into this and follow up with next steps."
        )
        return f"{opening}{code_line}{kb_line} {closing}"

    # -- Task 2 -------------------------------------------------------
    def _account_health(self, context: dict[str, Any]) -> dict:
        account = context.get("account")
        tickets = context.get("tickets", [])

        if account is None:
            return {
                "executive_summary": (
                    f"No account record was found for {context['account_id']} in the supplied "
                    "accounts dataset. No health assessment can be produced without account data; "
                    f"{len(tickets)} ticket(s) reference this account_id but cannot be attributed "
                    "to an account profile."
                ),
                "risks": [],
                "talking_points": [
                    {
                        "point": "Confirm the correct account_id with the customer's TAM before the next QBR.",
                        "basis": "account lookup returned no match in accounts.json",
                    }
                ],
            }

        health = account.get("health_status", "Unknown")
        trend = account.get("usage_trend", "Unknown")
        arr = account.get("arr_usd")
        company = account.get("company", context["account_id"])

        summary_bits = [
            f"{company} is currently marked '{health}' with a '{trend}' usage trend."
        ]
        if arr:
            summary_bits.append(f"The account represents ${arr:,} in ARR on the {account.get('plan_tier', 'Unknown')} plan.")
        if tickets:
            summary_bits.append(
                f"{len(tickets)} ticket(s) were logged in the last {context['lookback_days']} days, "
                f"and {len([t for t in tickets if t.get('urgency') == 'P1'])} of those were P1."
            )
        else:
            summary_bits.append(f"No tickets were logged for this account in the last {context['lookback_days']} days.")
        if account.get("escalation_notes"):
            summary_bits.append("Existing escalation notes flag: " + "; ".join(account["escalation_notes"][:2]) + ".")

        risks = []
        if health in ("At Risk", "Churning"):
            risks.append({
                "risk_type": "Account health",
                "severity": "Critical" if health == "Churning" else "High",
                "explanation": f"Account is classified as '{health}' with usage trend '{trend}'.",
                "supporting_ticket_id": tickets[0]["ticket_id"] if tickets else "N/A",
                "quote": (tickets[0]["subject"] if tickets else account.get("escalation_notes", ["No supporting ticket available"])[0]),
            })
        for note in account.get("escalation_notes", []):
            risks.append({
                "risk_type": "Escalation note",
                "severity": "High",
                "explanation": note,
                "supporting_ticket_id": tickets[0]["ticket_id"] if tickets else "N/A",
                "quote": note,
            })
        for t in tickets:
            if t.get("urgency") == "P1":
                risks.append({
                    "risk_type": "Open P1 incident",
                    "severity": "Critical",
                    "explanation": f"P1 ticket '{t['subject']}' in category {t.get('category')}.",
                    "supporting_ticket_id": t["ticket_id"],
                    "quote": t["subject"],
                })

        talking_points = []
        if health in ("At Risk", "Churning"):
            talking_points.append({
                "point": "Proactively address the account's health status and confirm ongoing pain points before renewal conversations.",
                "basis": f"health_status={health}",
            })
        if account.get("nps_score") is not None and account["nps_score"] <= 6:
            talking_points.append({
                "point": f"Discuss the low NPS score ({account['nps_score']}) directly and ask what would improve it.",
                "basis": "nps_score field",
            })
        if tickets:
            talking_points.append({
                "point": "Review recurring ticket themes with the customer and confirm root causes are resolved, not just tickets closed.",
                "basis": f"{len(tickets)} tickets in lookback window",
            })
        if not talking_points:
            talking_points.append({
                "point": "No urgent flags found; use the QBR to reinforce value delivered and explore expansion opportunities.",
                "basis": "no risk signals detected in available data",
            })

        return {
            "executive_summary": " ".join(summary_bits),
            "risks": risks,
            "talking_points": talking_points,
        }


class AnthropicLLMClient(LLMClient):
    """Real Anthropic Messages API client. Only used when explicitly configured."""

    name = "anthropic"

    def __init__(self) -> None:
        settings.require_anthropic_key()
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "LLM_PROVIDER=anthropic requires the 'anthropic' package. "
                "Install with `pip install anthropic`."
            ) from exc
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def complete_json(self, system_prompt: str, user_prompt: str, task: str, context: dict[str, Any]) -> dict:
        response = self._client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
        raw = "\n".join(text_blocks).strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)


def get_llm_client() -> LLMClient:
    """Factory that returns the configured provider. Defaults to mock."""
    if settings.llm_provider == "anthropic":
        return AnthropicLLMClient()
    return MockLLMClient()
