"""
API integration tests using FastAPI TestClient (synchronous) and httpx AsyncClient.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "ai_mode" in data


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "name" in data


def test_list_venues():
    r = client.get("/api/venues")
    assert r.status_code == 200
    venues = r.json()
    assert isinstance(venues, list)
    assert len(venues) >= 1


def test_get_venue():
    r = client.get("/api/venues/venue-stadium-a")
    assert r.status_code == 200
    venue = r.json()
    assert venue["id"] == "venue-stadium-a"
    assert "nodes" in venue
    assert "edges" in venue
    assert len(venue["nodes"]) == 18
    assert len(venue["edges"]) > 15


def test_get_venue_not_found():
    r = client.get("/api/venues/nonexistent")
    assert r.status_code == 404


def test_create_simulation():
    r = client.post("/api/simulations", json={
        "venue_id": "venue-stadium-a",
        "seed": 99,
        "simulation_id": "test-api-sim",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["simulation_id"] == "test-api-sim"
    assert data["status"] == "created"


def test_get_simulation():
    client.post("/api/simulations", json={
        "simulation_id": "test-get-sim",
    })
    r = client.get("/api/simulations/test-get-sim")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "created"


def test_get_simulation_not_found():
    r = client.get("/api/simulations/nonexistent")
    assert r.status_code == 404


def test_simulation_lifecycle():
    # Create
    r = client.post("/api/simulations", json={"simulation_id": "test-lifecycle"})
    assert r.status_code == 200

    # Start
    r = client.post("/api/simulations/test-lifecycle/start")
    assert r.status_code == 200
    assert r.json()["status"] == "running"

    # Pause
    r = client.post("/api/simulations/test-lifecycle/pause")
    assert r.status_code == 200
    assert r.json()["status"] == "paused"

    # Resume
    r = client.post("/api/simulations/test-lifecycle/resume")
    assert r.status_code == 200
    assert r.json()["status"] == "running"

    # Stop
    r = client.post("/api/simulations/test-lifecycle/stop")
    assert r.status_code == 200
    assert r.json()["status"] == "stopped"

    # Reset
    r = client.post("/api/simulations/test-lifecycle/reset")
    assert r.status_code == 200
    assert r.json()["status"] == "created"


def test_set_speed():
    client.post("/api/simulations", json={"simulation_id": "test-speed"})
    r = client.post("/api/simulations/test-speed/speed", json={"multiplier": 5.0})
    assert r.status_code == 200
    assert r.json()["speed_multiplier"] == 5.0


def test_parse_scenario():
    r = client.post("/api/scenarios/parse", json={
        "text": "A concert with 25,000 people starts at 8 PM through the east gate."
    })
    assert r.status_code == 200
    data = r.json()
    assert data["success"]
    assert data["parsed"]["crowdSize"] == 25000


def test_live_intelligence_reports_missing_server_key(monkeypatch):
    """A browser must never need or receive the TinyFish credential."""
    from app.core.config import settings
    monkeypatch.setattr(settings, "tinyfish_api_key", "")
    r = client.post("/api/intelligence/search", json={"query": "crowd safety guidance"})
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"].lower()


def test_simulation_state_snapshot():
    client.post("/api/simulations", json={"simulation_id": "test-state"})
    r = client.get("/api/simulations/test-state/state")
    assert r.status_code == 200
    snapshot = r.json()
    assert "simulation" in snapshot
    assert "metrics" in snapshot
    assert "safety" in snapshot
    assert "routing" in snapshot
    assert "ai" in snapshot


def test_emergency_requires_running_simulation():
    client.post("/api/simulations", json={"simulation_id": "test-em"})
    client.post("/api/simulations/test-em/start")
    # Trigger emergency
    r = client.post("/api/simulations/test-em/emergency", json={
        "type": "fire",
        "node_id": "j-n",
    })
    assert r.status_code == 200
    em = r.json()
    assert em["active"]
    assert em["type"] == "fire"

    # Clear emergency
    r = client.delete("/api/simulations/test-em/emergency")
    assert r.status_code == 200
    assert r.json()["status"] == "cleared"
