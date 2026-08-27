from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["llm_provider"] == "mock"


def test_triage_endpoint_valid_input():
    resp = client.post("/triage", json={"subject": "Slow reports", "body": "AnalyticsHub reports are very slow to load."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["classification"]["urgency"] in ("P1", "P2", "P3", "P4")


def test_triage_endpoint_rejects_empty_body():
    resp = client.post("/triage", json={"subject": "x", "body": ""})
    assert resp.status_code in (400, 422)


def test_account_health_endpoint_rejects_malformed_account_id():
    resp = client.post("/account-health", json={"account_id": "'; DROP TABLE accounts;--"})
    assert resp.status_code == 400


def test_account_health_endpoint_unknown_account_returns_404():
    resp = client.post("/account-health", json={"account_id": "ACC-00000"})
    assert resp.status_code == 404
