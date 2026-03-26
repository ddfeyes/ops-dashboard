"""E2E smoke tests — verify all API endpoints return 200 and expected structure."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json().get("status") in ("ok", "degraded")


def test_kanban_returns_list():
    """Kanban endpoint must return a JSON list (may be empty when GH_TOKEN is absent)."""
    r = client.get("/api/kanban")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_agents_returns_expected_keys():
    """Agents endpoint must return sessions and agents keys."""
    r = client.get("/api/agents")
    assert r.status_code == 200
    data = r.json()
    assert "sessions" in data
    assert "agents" in data


def test_system_returns_expected_keys():
    """System endpoint must return mac and hetzner keys."""
    r = client.get("/api/system")
    assert r.status_code == 200
    data = r.json()
    assert "mac" in data
    assert "hetzner" in data


def test_usage_returns_expected_keys():
    """Usage endpoint must return session/weekly token stats and source."""
    r = client.get("/api/usage")
    assert r.status_code == 200
    data = r.json()
    assert "current_session" in data
    assert "weekly_all" in data
    assert "source" in data


def test_crons_returns_list():
    """Crons endpoint must return a JSON list (may be empty in test env)."""
    r = client.get("/api/crons")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
