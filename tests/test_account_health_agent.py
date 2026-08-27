from src.agents.account_health_agent import run_account_health
from src.services.data_loader import get_data_store


def test_unknown_account_id_handled_gracefully():
    brief = run_account_health("ACC-00000")
    assert brief.metadata.account_found is False
    assert brief.executive_summary.strip()
    assert brief.risks == []
    assert brief.talking_points  # still gives the TAM something actionable


def test_known_account_produces_grounded_quotes():
    store = get_data_store()
    at_risk = next(a for a in store.accounts if a.health_status == "At Risk" and a.escalation_notes)
    brief = run_account_health(at_risk.account_id)
    assert brief.metadata.account_found is True
    for risk in brief.risks:
        # Every quote must literally appear in either a ticket or an
        # escalation note -- never fabricated.
        ticket = store.get_ticket(risk.supporting_ticket_id)
        haystacks = [n for n in at_risk.escalation_notes]
        if ticket:
            haystacks.append(ticket.subject)
            haystacks.append(ticket.body)
        assert any(risk.quote in h for h in haystacks)


def test_zero_ticket_account_does_not_fabricate_evidence():
    store = get_data_store()
    matched_ids = {t.account_id for t in store.tickets} & {a.account_id for a in store.accounts}
    no_tickets_account = next(a for a in store.accounts if a.account_id not in matched_ids)
    brief = run_account_health(no_tickets_account.account_id)
    assert brief.metadata.tickets_considered == 0
    for risk in brief.risks:
        assert risk.supporting_ticket_id == "N/A" or any(
            risk.quote in note for note in no_tickets_account.escalation_notes
        )


def test_deterministic_output_for_same_input():
    store = get_data_store()
    account_id = store.accounts[0].account_id
    brief1 = run_account_health(account_id, reference_date="2026-05-22T00:00:00Z")
    brief2 = run_account_health(account_id, reference_date="2026-05-22T00:00:00Z")
    assert brief1.model_dump() == brief2.model_dump()
