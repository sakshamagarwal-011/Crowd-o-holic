"""
Tests for risk engine and bottleneck detection.
"""
import pytest
from app.graph.edges import GraphEdge
from app.risk.engine import compute_safety_state
from app.risk.bottleneck import detect_bottlenecks
from app.services.venue_service import get_venue_for_simulation


def test_low_risk_state():
    graph = get_venue_for_simulation("venue-stadium-a")
    metrics = {
        "peopleCount": 100, "avgDensity": 0.1, "flowRate": 50,
        "avgSpeed": 1.2, "queueGrowth": 0.0, "capacityUtilization": 0.1,
        "queueLengths": {},
    }
    safety = compute_safety_state(graph, metrics, {}, set(), None, 0.0)
    assert safety["riskLevel"] == "low"
    assert safety["riskScore"] < 35


def test_high_risk_state():
    graph = get_venue_for_simulation("venue-stadium-a")
    # Set a high-density edge
    for e in graph.edges.values():
        e.density = 0.9
        e.flow = e.capacity * 0.9

    metrics = {
        "peopleCount": 5000, "avgDensity": 0.9, "flowRate": 500,
        "avgSpeed": 0.3, "queueGrowth": 5.0, "capacityUtilization": 0.9,
        "queueLengths": {},
    }
    safety = compute_safety_state(graph, metrics, {}, set(), None, 0.0)
    assert safety["riskScore"] >= 60
    assert safety["riskLevel"] in ("high", "critical", "emergency")


def test_bottleneck_detection():
    graph = get_venue_for_simulation("venue-stadium-a")
    # Set one edge to high density
    target_edge = next(iter(graph.edges.values()))
    target_edge.density = 0.85
    target_edge.flow = target_edge.capacity * 0.85

    metrics = {
        "peopleCount": 1000, "avgDensity": 0.4, "flowRate": 200,
        "avgSpeed": 0.8, "queueGrowth": 2.0, "capacityUtilization": 0.5,
        "queueLengths": {},
    }
    # Need to pass persistence ticks threshold (2)
    ticks = {target_edge.id: 2}
    bottlenecks, predicted = detect_bottlenecks(graph, metrics, ticks, 10.0)
    # Should detect the high-density edge as bottleneck
    assert len(bottlenecks) > 0
    bn = bottlenecks[0]
    assert bn["edgeId"] == target_edge.id or bn["currentDensity"] >= 0.7


def test_emergency_risk():
    from app.simulation.state import EmergencyRecord
    graph = get_venue_for_simulation("venue-stadium-a")
    em = EmergencyRecord(
        id="em-1", type="fire", location="Test", node_id="j-n",
        at_minute=5.0, active=True, closed_edge_ids=[], summary="Test emergency"
    )
    metrics = {
        "peopleCount": 100, "avgDensity": 0.1, "flowRate": 50,
        "avgSpeed": 1.2, "queueGrowth": 0.0, "capacityUtilization": 0.1,
        "queueLengths": {},
    }
    safety = compute_safety_state(graph, metrics, {}, set(), em, 5.0)
    assert safety["riskLevel"] == "emergency"
    # Emergency alert should be in alerts
    assert any("EMERGENCY" in a["title"] for a in safety["alerts"])


def test_bottleneck_hysteresis():
    """Bottlenecks should not trigger immediately — need persistence ticks."""
    graph = get_venue_for_simulation("venue-stadium-a")
    target_edge = next(iter(graph.edges.values()))
    target_edge.density = 0.85

    metrics = {"peopleCount": 100, "avgDensity": 0.5, "flowRate": 200,
               "avgSpeed": 0.8, "queueGrowth": 2.0, "capacityUtilization": 0.5,
               "queueLengths": {}}

    # First tick — should NOT be confirmed yet
    ticks: dict[str, int] = {}
    bottlenecks, _ = detect_bottlenecks(graph, metrics, ticks, 0.0)
    # Persistence counter should be 1 now
    assert ticks.get(target_edge.id, 0) >= 1

    # After persistence threshold — should be confirmed
    ticks[target_edge.id] = 5
    bottlenecks, _ = detect_bottlenecks(graph, metrics, ticks, 0.0)
    assert len(bottlenecks) > 0


def test_alert_generation():
    graph = get_venue_for_simulation("venue-stadium-a")
    for e in graph.edges.values():
        e.density = 0.9

    metrics = {
        "peopleCount": 5000, "avgDensity": 0.9, "flowRate": 500,
        "avgSpeed": 0.3, "queueGrowth": 5.0, "capacityUtilization": 0.9,
        "queueLengths": {},
    }
    ticks = {e.id: 10 for e in graph.edges.values()}
    safety = compute_safety_state(graph, metrics, ticks, set(), None, 10.0)
    assert len(safety["alerts"]) > 0
    for alert in safety["alerts"]:
        assert "id" in alert
        assert "severity" in alert
        assert "title" in alert
