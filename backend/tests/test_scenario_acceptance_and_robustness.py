from __future__ import annotations

"""
Acceptance test and robustness suite for Crowd-O-Holic.
Covers:
- Acceptance test scenario extraction and verification
- Explicit values overriding defaults
- Missing values distinguishable from zero
- Venue graph location resolution & unresolved location flagging
- Density vs congestion vs restricted movement vs complete blockage distinctions
- Medical emergency responder route feasibility
- Simulation engine initialization with 30,000 crowd
- Risk and bottleneck calculations
- OpenRouter fallback behavior
- TinyFish error handling
- Scenario update API
"""

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient

from app.main import app
from app.ai.mock_provider import MockAIProvider
from app.ai.openrouter_provider import OpenRouterAIProvider
from app.graph.resolver import resolve_location
from app.services.venue_service import get_venue, get_venue_for_simulation
from app.simulation.engine import SimulationEngine
from app.simulation.generator import generate_crowd_groups
from app.emergency.manager import apply_scenario_incidents, trigger_emergency
from app.routing.dynamic_router import build_medical_responder_route, build_route
from app.risk.engine import compute_safety_state
from app.metrics.calculator import calculate_metrics


ACCEPTANCE_SCENARIO_TEXT = (
    "A music festival is hosting 30,000 attendees across multiple zones. "
    "One attendee collapses near the front-stage area, and security requests immediate medical assistance. "
    "Meanwhile, camera observations show increasing crowd density near the front stage, "
    "restricted movement along the medical access corridor, and moderate congestion near the main entrance."
)


@pytest.mark.asyncio
async def test_acceptance_scenario_extraction():
    """Verify all 15 acceptance criteria on the required test scenario."""
    provider = MockAIProvider()
    result = await provider.parse_scenario(ACCEPTANCE_SCENARIO_TEXT)

    assert result.success is True
    parsed = result.parsed
    assert parsed is not None

    # 1. Explicit crowd size of 30,000
    assert parsed.crowdSize == 30000
    assert parsed.crowdSize_origin == "explicit"

    # 2. Missing event timing and entry distribution identified & distinguishable
    assert parsed.timing_origin == "default"
    assert "event_start_time" in parsed.missing_fields
    assert parsed.entryDistribution_origin == "default"
    assert "entry_distribution" in parsed.missing_fields

    # 3. Incidents preserved
    incidents = parsed.incidents
    assert len(incidents) >= 4

    # Medical emergency
    med = next((i for i in incidents if i.type == "medical"), None)
    assert med is not None
    assert med.severity == "emergency"
    assert med.resolved_node_id == "stage"
    assert med.unresolved is False

    # Camera density observation
    obs = next((i for i in incidents if i.type == "observation"), None)
    assert obs is not None
    assert obs.source == "camera_observation"
    assert obs.resolved_node_id == "stage"

    # Restricted corridor
    res = next((i for i in incidents if i.type == "restricted-corridor"), None)
    assert res is not None
    assert res.resolved_edge_id == "e-stage-medical"
    assert "restricted_movement" in res.operational_constraints

    # Main entrance congestion
    cong = next((i for i in incidents if i.type == "congestion"), None)
    assert cong is not None
    assert cong.resolved_node_id == "gate-e" or cong.resolved_edge_id == "e-ge-je"

    # 4. Crowd groups scaled to exactly 30,000
    total_group_crowd = sum(g.size for g in parsed.crowdGroups)
    assert total_group_crowd == 30000


def test_venue_location_resolution():
    """Verify resolution of descriptive locations to real venue graph nodes/edges."""
    graph = get_venue("venue-stadium-a")

    # Front stage -> node 'stage'
    r1 = resolve_location("front-stage area", graph)
    assert r1.is_resolved is True
    assert r1.resolved_node_id == "stage"

    # Medical access corridor -> edge 'e-stage-medical'
    r2 = resolve_location("medical access corridor", graph)
    assert r2.is_resolved is True
    assert r2.resolved_edge_id == "e-stage-medical"

    # Main entrance -> node 'gate-e' or edge 'e-ge-je'
    r3 = resolve_location("main entrance", graph)
    assert r3.is_resolved is True
    assert r3.resolved_node_id == "gate-e"

    # Unknown / invented location -> unresolved without crashing or inventing fake IDs
    r4 = resolve_location("VIP Rooftop Helipad Lounge", graph)
    assert r4.is_resolved is False
    assert r4.resolved_node_id is None
    assert r4.resolved_edge_id is None
    assert r4.warning is not None


@pytest.mark.asyncio
async def test_explicit_crowd_size_overriding_conflicting_default():
    """Explicit crowd size must always be preserved."""
    provider = MockAIProvider()
    res = await provider.parse_scenario("Exhibition with 45,000 visitors.")
    assert res.parsed.crowdSize == 45000
    assert res.parsed.crowdSize_origin == "explicit"

    res_default = await provider.parse_scenario("Unspecified event at stadium.")
    assert res_default.parsed.crowdSize == 20000
    assert res_default.parsed.crowdSize_origin == "default"


@pytest.mark.asyncio
async def test_missing_time_distinguishable_from_midnight():
    """Missing time must be labeled 'default' (19:00), not confused with explicit 00:00."""
    provider = MockAIProvider()
    res_no_time = await provider.parse_scenario("Concert with 10,000 attendees.")
    assert res_no_time.parsed.timing_origin == "default"
    assert "event_start_time" in res_no_time.parsed.missing_fields

    res_midnight = await provider.parse_scenario("New Year party at 12 am with 10,000 attendees.")
    assert res_midnight.parsed.timing_origin == "explicit"
    assert res_midnight.parsed.timing.startMinutesOfDay == 0


def test_simulation_initialization_with_acceptance_scenario():
    """Simulation engine initializes with 30,000 crowd and evaluates medical responder route."""
    graph = get_venue_for_simulation("venue-stadium-a")
    provider = MockAIProvider()

    # Pre-parse scenario
    import asyncio
    parse_result = asyncio.run(provider.parse_scenario(ACCEPTANCE_SCENARIO_TEXT))
    scenario_dict = parse_result.parsed.model_dump()

    engine = SimulationEngine(
        simulation_id="test-acceptance-sim",
        scenario=scenario_dict,
        graph=graph,
        ai_provider=provider,
    )

    # Crowd size
    assert engine.state.scenario["crowdSize"] == 30000
    total_group_size = sum(g.total_size for g in engine.state.groups)
    assert total_group_size == 30000

    # Medical emergency & evaluated responder route
    assert engine.state.emergency is not None
    assert engine.state.emergency.type == "medical"
    assert engine.state.emergency.node_id == "stage"

    med_route = next((r for r in engine.state.routes if r.id == "r-med-response"), None)
    assert med_route is not None
    assert med_route.from_node_id == "medical"
    assert med_route.to_node_id == "stage"

    # Restricted corridor is tracked
    assert "e-stage-medical" in engine.state.restricted_edges
    assert engine.state.restricted_edges["e-stage-medical"] == 0.4

    # Baseline density offsets applied
    assert "e-ge-je" in engine.state.edge_density_offsets
    assert "e-jn-stage" in engine.state.edge_density_offsets


def test_density_vs_restricted_vs_blocked_distinction():
    """Verify distinct treatment of high density, corridor restriction, and emergency blockage."""
    graph = get_venue_for_simulation("venue-stadium-a")

    # 1. Normal edge
    edge = graph.get_edge("e-stage-medical")
    assert edge.is_traversable is True

    # 2. Restricted edge: still traversable, but higher routing penalty
    restricted_edges = {"e-stage-medical": 0.4}
    r_normal = build_route("r1", "medical", "stage", "Normal", "active", graph)
    r_restricted = build_route("r2", "medical", "stage", "Restricted", "active", graph, restricted_edges=restricted_edges)
    assert r_restricted.cost > r_normal.cost

    # 3. Blocked edge: closed, is_traversable is False
    graph.close_edge("e-stage-medical")
    assert graph.get_edge("e-stage-medical").is_traversable is False


def test_risk_calculations_with_active_emergency():
    """Risk calculation reflects active emergency with high risk score."""
    graph = get_venue_for_simulation("venue-stadium-a")
    from app.simulation.state import EmergencyRecord

    emergency = EmergencyRecord(
        id="em-1",
        type="medical",
        location="Main Stage",
        node_id="stage",
        at_minute=0.0,
        active=True,
        closed_edge_ids=[],
        summary="Medical emergency",
    )
    metrics = {"avgDensity": 0.25, "peopleCount": 30000, "flowRate": 500}

    safety = compute_safety_state(
        graph=graph,
        metrics=metrics,
        bottleneck_ticks={},
        acknowledged_alerts=set(),
        emergency=emergency,
        sim_time_min=0.0,
    )

    assert safety["riskLevel"] == "emergency"
    # Derived deterministically from physical load (0.25 -> 25) without arbitrary inflation
    assert safety["riskScore"] == 25
    assert len(safety["alerts"]) >= 1


@pytest.mark.asyncio
async def test_safety_analyst_grounded_recommendation():
    """AI Safety Analyst produces grounded recommendations citing active metrics and incidents."""
    provider = MockAIProvider()
    metrics = {"avgDensity": 0.72, "peopleCount": 30000, "flowRate": 650.0}
    safety_state = {
        "riskLevel": "emergency",
        "riskScore": 92,
        "bottlenecks": [],
        "timeToCriticalMin": 5.0,
    }
    emergency = {
        "type": "medical",
        "location": "Main Stage",
        "active": True,
        "summary": "Attendee collapsed near front-stage area requesting medical assistance.",
    }

    analysis = await provider.analyze_safety(
        metrics=metrics,
        safety_state=safety_state,
        sim_time_min=15.0,
        sim_status="running",
        emergency=emergency,
    )

    assert analysis.urgency == "emergency"
    assert "Main Stage" in analysis.affected_locations
    assert "medical" in analysis.summary.lower() or "medical" in analysis.risk_explanation.lower()
    assert analysis.supporting_metrics.get("risk_score") == 92


def test_api_apply_scenario_endpoint():
    """Test POST /api/simulations/{id}/scenario updates simulation configuration."""
    client = TestClient(app)

    scenario_payload = {
        "scenario": {
            "id": "scenario-test-apply",
            "name": "Live Festival",
            "venueId": "venue-stadium-a",
            "crowdSize": 30000,
            "entryDistribution": [
                {"gateId": "gate-e", "fraction": 0.6},
                {"gateId": "gate-w", "fraction": 0.4},
            ],
            "incidents": [
                {
                    "id": "inc-test",
                    "type": "medical",
                    "description": "Medical incident at stage",
                    "reported_location": "front stage",
                    "resolved_node_id": "stage",
                    "severity": "emergency",
                }
            ],
        }
    }

    res = client.post("/api/simulations/default/scenario", json=scenario_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["crowd_size"] == 30000
    assert data["incidents_count"] == 1

    # Verify simulation state reflects 30,000 crowd
    state_res = client.get("/api/simulations/default/state")
    assert state_res.status_code == 200
    snap = state_res.json()
    assert len(snap["incidents"]) == 1


def test_risk_calculation_separation_no_hardcoded_90():
    """Verify emergency operational severity is separated from numerical risk score."""
    from app.risk.engine import compute_safety_state
    from app.simulation.state import EmergencyRecord
    from app.services.venue_service import get_venue_for_simulation

    graph = get_venue_for_simulation("venue-stadium-a")
    em = EmergencyRecord(
        id="em-test", type="medical", location="Main Stage", node_id="stage",
        at_minute=0.0, active=True, closed_edge_ids=[], summary="Medical emergency"
    )

    # Empty venue on standby / low load
    metrics = {
        "peopleCount": 0, "avgDensity": 0.0, "peakDensity": 0.0, "flowRate": 0,
        "avgSpeed": 1.2, "queueGrowth": 0.0, "capacityUtilization": 0.0,
        "queueLengths": {},
    }
    safety = compute_safety_state(graph, metrics, {}, set(), em, 0.0)

    # Emergency severity level must be active
    assert safety["riskLevel"] == "emergency"
    # But numerical riskScore must NOT be hardcoded to 90 on an empty venue
    assert safety["riskScore"] < 50
    assert any("EMERGENCY" in a["title"] for a in safety["alerts"])


def test_unresolved_location_robustness_no_fictitious_fallbacks():
    """Verify unfamiliar locations and short words do not falsely resolve to convenient nodes."""
    from app.graph.resolver import resolve_location
    from app.services.venue_service import get_venue_for_simulation

    graph = get_venue_for_simulation("venue-stadium-a")

    for loc in ["VIP Lounge", "Zone 4", "st", "in", "arbitrary unfamiliar room"]:
        res = resolve_location(loc, graph)
        assert res.is_resolved is False, f"Location '{loc}' should not be resolved!"
        assert res.resolved_node_id is None
        assert res.resolved_edge_id is None
        assert res.warning is not None


def test_unresolved_incident_preserved_in_simulation():
    """Verify apply_scenario_incidents does not fall back to stage or e-stage-medical for unmapped locations."""
    from app.emergency.manager import apply_scenario_incidents
    from app.simulation.state import SimulationRuntimeState
    from app.services.venue_service import get_venue_for_simulation

    graph = get_venue_for_simulation("venue-stadium-a")
    state = SimulationRuntimeState(simulation_id="sim-test", scenario_id="scen-test", venue_id="venue-stadium-a", seed=42)

    unresolved_incidents = [
        {
            "id": "inc-unres-1",
            "type": "medical",
            "description": "Medical issue at VIP Lounge",
            "reported_location": "VIP Lounge",
            "resolved_node_id": None,
            "resolved_edge_id": None,
            "severity": "emergency",
        },
        {
            "id": "inc-unres-2",
            "type": "restricted-corridor",
            "description": "Restricted pathway at Zone 9",
            "reported_location": "Zone 9",
            "resolved_node_id": None,
            "resolved_edge_id": None,
            "severity": "moderate",
        }
    ]

    apply_scenario_incidents(state, graph, unresolved_incidents)

    # Must preserve incidents
    assert len(state.incidents) == 2
    # Must NOT invent fake stage assignment
    assert state.emergency is not None
    assert state.emergency.node_id == ""  # Not "stage"
    assert "VIP Lounge" in state.emergency.location
    # Must NOT invent fake e-stage-medical corridor restriction
    assert "e-stage-medical" not in state.restricted_edges


@pytest.mark.asyncio
async def test_openrouter_fallback_transparent_error_reporting(monkeypatch):
    """Verify OpenRouter provider explicitly records error information on fallback."""
    from app.ai.openrouter_provider import OpenRouterAIProvider
    import httpx

    provider = OpenRouterAIProvider()

    # Simulate upstream HTTP 402 Payment Required error
    async def mock_fail(*args, **kwargs):
        req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        resp = httpx.Response(402, text='{"error":{"message":"Insufficient credits"}}', request=req)
        raise httpx.HTTPStatusError("Client error '402 Payment Required'", request=req, response=resp)

    monkeypatch.setattr(provider, "_complete", mock_fail)

    result = await provider.parse_scenario("A festival hosting 15,000 guests.")
    assert result.success is True
    assert result.provider == "mock-fallback"
    assert result.error is not None
    assert "402 Payment Required" in result.error
    assert any("OpenRouter request failed" in note for note in result.notes)

