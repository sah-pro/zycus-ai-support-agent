"""Loads and indexes the supplied mock dataset (tickets.json, accounts.json).

This is the *only* place that reads the dataset files. Loading is cached
(single read per process) since the dataset is static and small (500 + 50
records) -- no database needed at this scale.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from src.config.settings import settings
from src.models.domain import Account, Ticket


class DataStore:
    """In-memory index over the supplied JSON dataset."""

    def __init__(self, tickets: list[Ticket], accounts: list[Account]):
        self.tickets = tickets
        self.accounts = accounts
        self._account_by_id = {a.account_id: a for a in accounts}
        self._tickets_by_account: dict[str, list[Ticket]] = {}
        for t in tickets:
            if t.account_id:
                self._tickets_by_account.setdefault(t.account_id, []).append(t)

    def get_account(self, account_id: str) -> Account | None:
        return self._account_by_id.get(account_id)

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        for t in self.tickets:
            if t.ticket_id == ticket_id:
                return t
        return None

    def tickets_for_account(
        self,
        account_id: str,
        reference_date: datetime,
        lookback_days: int,
    ) -> list[Ticket]:
        """Tickets for `account_id` created within `lookback_days` of `reference_date`.

        Uses a caller-supplied reference date (rather than `datetime.now()`)
        so results are reproducible across runs -- required for Task 2's
        determinism requirement. Results are sorted by `created_at`
        descending, then by `ticket_id` ascending as a stable tiebreaker, so
        ordering never depends on JSON file iteration order.
        """
        cutoff = reference_date - timedelta(days=lookback_days)
        candidates = self._tickets_by_account.get(account_id, [])

        def _created_at(t: Ticket) -> datetime:
            if not t.created_at:
                return datetime.min.replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(t.created_at.replace("Z", "+00:00"))

        in_window = [t for t in candidates if _created_at(t) > cutoff]
        return sorted(in_window, key=lambda t: (-_created_at(t).timestamp(), t.ticket_id))


def _load_json(path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def get_data_store() -> DataStore:
    """Load the dataset once per process and cache it.

    Raises FileNotFoundError with a clear message if the supplied dataset
    files are missing, rather than failing deep inside a pipeline.
    """
    if not settings.tickets_path.exists() or not settings.accounts_path.exists():
        raise FileNotFoundError(
            f"Expected dataset files at {settings.tickets_path} and "
            f"{settings.accounts_path}. Did you copy the starter repo's "
            "data/ directory into this project?"
        )
    tickets = [Ticket.model_validate(t) for t in _load_json(settings.tickets_path)]
    accounts = [Account.model_validate(a) for a in _load_json(settings.accounts_path)]
    return DataStore(tickets=tickets, accounts=accounts)
