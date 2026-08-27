"""Loads versioned prompt templates from src/prompts/."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


@lru_cache(maxsize=None)
def load_prompt(name: str) -> tuple[str, str]:
    """Load a prompt file and split it into (system_prompt, user_template).

    Prompt files use a `SYSTEM:` / `USER TEMPLATE:` split so a single file
    documents the whole exchange for a given prompt version.
    """
    path = PROMPTS_DIR / f"{name}.txt"
    raw = path.read_text(encoding="utf-8")
    _, _, rest = raw.partition("SYSTEM:")
    system_part, _, user_part = rest.partition("USER TEMPLATE:")
    return system_part.strip(), user_part.strip()
