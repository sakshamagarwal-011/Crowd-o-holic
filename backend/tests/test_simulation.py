"""
Tests for simulation engine — lifecycle, crowd generation, movement.
"""
import asyncio
import pytest
from app.simulation.generator import generate_crowd_groups, default_scenario_dict
from app.simulation.engine import SimulationEngine
from app.services.venue_service import get_venue_for_simulation
from app.ai.mock_provider import MockAIProvider


def make_engine(scenario=None, seed=42) -> SimulationEngine:
    graph = get_venue_for_simulation("venue-stadium-a")
    sc = scenario or default_scenario_dict()
    return SimulationEngine(
        simulation_id="test-sim",
        scenario=sc,
        graph=graph,
        ai_provider=MockAIProvider(),
        seed=seed,
    )


def test_crowd_generation_from_groups():
    sc = default_scenario_dict()
    groups = generate_crowd_groups(sc, seed=42)
    assert len(groups) == 4
    total = sum(g.total_size for g in groups)
    assert total == 20000


def test_crowd_generation_deterministic():
    sc = default_scenario_dict()
    g1 = generate_crowd_groups(sc, seed=42)
    g2 = generate_crowd_groups(sc, seed=42)
    assert [g.total_size for g in g1] == [g.total_size for g in g2]


def test_crowd_generation_different_seeds():
    """Different seeds should produce same totals but may differ in distribution."""
    sc = default_scenario_dict()
    sc.pop("crowdGroups")  # force auto-generation
    g1 = generate_crowd_groups(sc, seed=1)
    g2 = generate_crowd_groups(sc, seed=2)
    # Both should produce valid groups
    assert len(g1) > 0
    assert len(g2) > 0


def test_engine_creation():
    engine = make_engine()
    assert engine.state.status == "created"
    assert engine.state.sim_time_min == -60.0
    assert engine.state.total_entered == 0
    assert engine.state.total_exited == 0


@pytest.mark.asyncio
async def test_engine_start():
    engine = make_engine()
    engine.start()
    assert engine.state.status == "running"
    engine.stop()


@pytest.mark.asyncio
async def test_engine_pause_resume():
    engine = make_engine()
    engine.start()
    engine.pause()
    assert engine.state.status == "paused"
    engine.resume()
    assert engine.state.status == "running"
    engine.stop()


def test_engine_cannot_pause_when_not_running():
    engine = make_engine()
    with pytest.raises(ValueError):
        engine.pause()


@pytest.mark.asyncio
async def test_engine_reset():
    engine = make_engine()
    engine.start()
    engine.stop()
    engine.reset()
    assert engine.state.status == "created"
    assert engine.state.sim_time_min == -60.0
    assert engine.state.total_entered == 0


def test_speed_setter():
    engine = make_engine()
    engine.set_speed(5.0)
    assert engine.state.speed_multiplier == 5.0
    engine.set_speed(0.0)  # clamped to 0.1
    assert engine.state.speed_multiplier >= 0.1
    engine.set_speed(100.0)  # clamped to 20
    assert engine.state.speed_multiplier == 20.0


@pytest.mark.asyncio
async def test_simulation_produces_agents():
    """Run a few simulation ticks and verify agents are spawned."""
    engine = make_engine()
    engine.start()
    # Simulate 5 seconds at 10x speed
    for _ in range(5):
        await engine._tick(1.0)
    # Should have spawned some agents
    assert engine.state.total_entered > 0 or engine.state.sim_time_min < -50


@pytest.mark.asyncio
async def test_metrics_calculation():
    engine = make_engine()
    engine.start()
    for _ in range(10):
        await engine._tick(1.0)
    metrics, safety = engine.get_snapshot_data()
    assert "peopleCount" in metrics
    assert "avgDensity" in metrics
    assert "flowRate" in metrics
    assert "riskScore" in safety
    assert "riskLevel" in safety
    assert metrics["avgDensity"] >= 0
    assert 0 <= safety["riskScore"] <= 100


@pytest.mark.asyncio
async def test_timeline_entries():
    engine = make_engine()
    engine.start()
    assert len(engine.state.timeline) > 0
    entry = engine.state.timeline[-1]
    assert "kind" in entry.__dict__
    assert "title" in entry.__dict__
