"""Centralized application configuration.

All tunable values live here. Nothing in the rest of the codebase should
hard-code a magic constant that belongs in config, and nothing here should
ever hold a real secret -- secrets come from environment variables only,
loaded from a local, git-ignored `.env` file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Load a local .env file if python-dotenv is available. This is optional --
# the app must run correctly even with no .env file and no dotenv package.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - optional dependency
    pass

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Immutable application settings, resolved once at import time."""

    # --- LLM provider ---------------------------------------------------
    # "mock" (default, no network/API key needed) or "anthropic".
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock").strip().lower())
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    anthropic_model: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    )
    llm_temperature: float = 0.0  # deterministic by default across both providers
    llm_max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "1500")))

    # --- Data paths -------------------------------------------------------
    data_dir: Path = REPO_ROOT / "data"
    knowledge_base_dir: Path = REPO_ROOT / "knowledge-base"
    tickets_path: Path = REPO_ROOT / "data" / "tickets.json"
    accounts_path: Path = REPO_ROOT / "data" / "accounts.json"

    # --- Determinism ------------------------------------------------------
    # Task 2 requires deterministic account-health output. Rather than use
    # datetime.now() (which silently changes the 90-day ticket window on
    # every run and would break reproducibility of a fixed test fixture),
    # callers may pin an explicit reference date. This default is used only
    # when no reference date is supplied by the caller/tests.
    default_reference_date: str = field(
        default_factory=lambda: os.getenv("REFERENCE_DATE", "2026-05-22T00:00:00Z")
    )
    account_health_lookback_days: int = 90

    # --- Retrieval ----------------------------------------------------
    retrieval_top_k: int = 3
    # Minimum normalized BM25 score for a retrieval hit to count as a
    # genuine "strong" match. The index returns any hit with a positive
    # score (including weak, incidental term overlap), but "known_issue"
    # must never be based on a weak match -- see guard_known_issue.
    min_kb_relevance_score: float = 0.35

    # --- Logging ------------------------------------------------------
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    def require_anthropic_key(self) -> None:
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise RuntimeError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
                "Set it in your local .env (never commit it), or switch "
                "LLM_PROVIDER back to 'mock'."
            )


settings = Settings()
