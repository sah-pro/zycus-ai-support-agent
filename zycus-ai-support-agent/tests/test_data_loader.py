from datetime import datetime, timezone

from src.models.domain import Account, Ticket
from src.services.data_loader import DataStore, get_data_store


def _make_ticket(ticket_id: str, account_id: str, created_at: str) -> Ticket:
    return Ticket(ticket_id=ticket_id, account_id=account_id, subject="s", body="b", created_at=created_at)


def test_tickets_for_account_filters_by_90_day_window():
    store = DataStore(
        tickets=[
            _make_ticket("T1", "ACC-1", "2026-05-01T00:00:00Z"),  # within window
            _make_ticket("T2", "ACC-1", "2025-01-01T00:00:00Z"),  # outside window
        ],
        accounts=[],
    )
    reference = datetime(2026, 5, 22, tzinfo=timezone.utc)
    result = store.tickets_for_account("ACC-1", reference_date=reference, lookback_days=90)
    assert [t.ticket_id for t in result] == ["T1"]


def test_missing_account_returns_none():
    store = DataStore(tickets=[], accounts=[Account(account_id="ACC-9")])
    assert store.get_account("ACC-999") is None
    assert store.get_account("ACC-9") is not None


def test_stable_sort_order_is_deterministic():
    store = DataStore(
        tickets=[
            _make_ticket("T2", "ACC-1", "2026-05-01T00:00:00Z"),
            _make_ticket("T1", "ACC-1", "2026-05-01T00:00:00Z"),  # same timestamp, tie-broken by id
        ],
        accounts=[],
    )
    reference = datetime(2026, 5, 22, tzinfo=timezone.utc)
    result = store.tickets_for_account("ACC-1", reference_date=reference, lookback_days=90)
    assert [t.ticket_id for t in result] == ["T1", "T2"]


def test_real_dataset_loads_without_error():
    store = get_data_store()
    assert len(store.tickets) == 500
    assert len(store.accounts) == 50
