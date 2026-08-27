"""Enum values taken verbatim from DATA_SCHEMA.md.

Centralizing these lets classification / validation code check membership
instead of re-typing string literals, and gives the LLM prompts a single
source of truth to interpolate into their instructions.
"""
from __future__ import annotations

PRODUCTS = ["DataBridge Pro", "CloudSync", "AnalyticsHub", "SecureVault", "WorkflowEngine"]

CATEGORIES = [
    "Bug",
    "Feature Request",
    "How-To",
    "Performance",
    "Billing",
    "Integration",
    "Onboarding",
    "Data Loss",
]

URGENCIES = ["P1", "P2", "P3", "P4"]

STATUSES = ["Open", "In Progress", "Pending Customer", "Resolved", "Closed"]

PLAN_TIERS = ["Starter", "Professional", "Business", "Enterprise"]

CHANNELS = ["email", "portal", "chat", "phone"]

RECOMMENDED_TEAMS = [
    "Tier-1 Support",
    "Tier-2 Support",
    "Product Engineering",
    "Billing & Accounts",
    "Onboarding & Customer Success",
    "Security & Compliance",
]

# Keyword -> urgency signal, used as a deterministic pre-classification hint
# before the LLM sees the ticket. This does not decide urgency by itself; it
# gives the LLM a grounded starting signal and lets the eval harness check
# obvious P1 language is not missed.
URGENCY_KEYWORDS = {
    "P1": [
        "production down",
        "production system is completely down",
        "completely down",
        "system is down",
        "business stopped",
        "complete outage",
        "all users affected",
        "all users are unable",
        "unable to access the service",
        "data breach",
        "cannot access any",
        "critical",
        "urgent escalation",
    ],
    "P2": [
        "major impact",
        "significant workaround",
        "blocking",
        "urgently",
        "47 users",
        "impacting",
    ],
}

# Common error codes documented in the knowledge base -- used for
# deterministic "known issue" detection via regex before the LLM runs.
KNOWN_ERROR_CODE_PATTERN = r"\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b"
