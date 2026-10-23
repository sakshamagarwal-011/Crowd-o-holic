from __future__ import annotations

"""
Simulation service — registry of all active simulations.
Multiple simulations are isolated from each other.
"""

import uuid
from typing import Any

from app.simulation.engine import SimulationEngine
from app.core.exceptions import SimulationNotFoundError, SimulationStateError
from app.core.logging import get_logger

log = get_logger(__name__)

# In-memory registry: simulation_id → SimulationEngine
_registry: dict[str, SimulationEngine] = {}


def create_simulation(
    scenario: dict[str, Any],
    graph,
    ai_provider,
    seed: int = 42,
    simulation_id: str | None = None,
) -> SimulationEngine:
    """Create and register a new simulation."""
    sim_id = simulation_id or str(uuid.uuid4())
    engine = SimulationEngine(
        simulation_id=sim_id,
        scenario=scenario,
        graph=graph,
        ai_provider=ai_provider,
        seed=seed,
    )
    _registry[sim_id] = engine
    log.info("Simulation registered | id=%s", sim_id)
    return engine


def get_simulation(simulation_id: str) -> SimulationEngine:
    engine = _registry.get(simulation_id)
    if engine is None:
        if simulation_id == "default":
            return get_or_create_default()
        raise SimulationNotFoundError(simulation_id)
    return engine


def get_or_create_default(graph=None, ai_provider=None) -> SimulationEngine:
    """Get the default simulation or create one with the default scenario."""
    if "default" in _registry:
        return _registry["default"]
    if graph is None:
        from app.services.venue_service import get_venue_for_simulation
        graph = get_venue_for_simulation("venue-stadium-a")
    if ai_provider is None:
        from app.services.ai_service import get_ai_provider
        ai_provider = get_ai_provider()
    from app.simulation.generator import default_scenario_dict
    scenario = default_scenario_dict()
    return create_simulation(scenario, graph, ai_provider, seed=42, simulation_id="default")


def list_simulations() -> list[str]:
    return list(_registry.keys())


def remove_simulation(simulation_id: str) -> None:
    engine = _registry.pop(simulation_id, None)
    if engine:
        try:
            engine.stop()
        except Exception:
            pass
