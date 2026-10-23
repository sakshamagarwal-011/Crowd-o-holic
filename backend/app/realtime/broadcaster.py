from __future__ import annotations

"""
Snapshot serializer and broadcaster.
Converts simulation runtime state into frontend-compatible SimSnapshot
and broadcasts it through the connection manager.
"""

import math
import time
from typing import Any, TYPE_CHECKING

from app.realtime.connection_manager import connection_manager
from app.realtime.events import make_event
from app.simulation.state import SimulationRuntimeState
from app.graph.graph import VenueGraph

if TYPE_CHECKING:
    pass


def build_snapshot(
    sim_state: SimulationRuntimeState,
    graph: VenueGraph,
    metrics: dict[str, Any],
    safety_state: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a SimSnapshot dict matching the frontend's SimSnapshot type exactly.
    """
    # Agents (visual cap)
    agents = [a.to_frontend_dict() for a in sim_state.agents]

    # Simulation state
    simulation = {
        "status": _map_status(sim_state.status),
        "simTimeMin": round(sim_state.sim_time_min, 2),
        "speedMultiplier": sim_state.speed_multiplier,
        "agents": agents,
        "totalActive": len(sim_state.agents),
        "totalEntered": sim_state.total_entered,
        "totalExited": sim_state.total_exited,
    }

    # Routing state
    active_routes = [r.to_frontend_dict() for r in sim_state.routes
                     if r.status in ("active", "congested")]
    alt_routes = [r.to_frontend_dict() for r in sim_state.routes
                  if r.status == "recommended"]
    recent_changes = [rc.to_frontend_dict() for rc in sim_state.route_changes[:5]]

    edge_states = {e.id: e.to_frontend_dict() for e in graph.edges.values()}


    routing = {
        "activeRoutes": active_routes,
        "alternativeRoutes": alt_routes,
        "disabledEdges": list(sim_state.disabled_edges),
        "recentChanges": recent_changes,
        "edges": edge_states,
    }


    # AI state
    ai_state = _build_ai_state(sim_state)

    # Emergency
    emergency = sim_state.emergency.to_frontend_dict() if sim_state.emergency else None

    # Timeline
    timeline = [t.to_frontend_dict() for t in sim_state.timeline[:30]]

    return {
        "simulation": simulation,
        "metrics": metrics,
        "safety": safety_state,
        "routing": routing,
        "ai": ai_state,
        "emergency": emergency,
        "timeline": timeline,
        "incidents": [
            inc if isinstance(inc, dict) else inc.to_frontend_dict()
            for inc in sim_state.incidents
        ],
        "edges": edge_states,
    }


def _map_status(backend_status: str) -> str:
    """Map backend status to frontend SimulationStatus."""
    mapping = {
        "created": "idle",
        "running": "running",
        "paused": "paused",
        "stopped": "idle",
        "completed": "completed",
        "failed": "error",
    }
    return mapping.get(backend_status, "idle")


def _build_ai_state(sim_state: SimulationRuntimeState) -> dict:
    """Build frontend AIState from simulation AI state."""
    current = sim_state.ai_current
    history = sim_state.ai_history

    analyst_stage = sim_state.ai_stage or "idle"

    return {
        "scenario": {
            "rawText": "",
            "stage": "idle",
            "extracted": None,
            "notes": [],
        },
        "analyst": {
            "stage": analyst_stage,
            "current": current,
            "history": history,
        },
    }


async def broadcast_snapshot(
    simulation_id: str,
    sim_state: SimulationRuntimeState,
    graph: VenueGraph,
    metrics: dict[str, Any],
    safety_state: dict[str, Any],
) -> None:
    """Serialize and broadcast the current simulation snapshot."""
    snapshot = build_snapshot(sim_state, graph, metrics, safety_state)
    event = make_event("simulation.updated", snapshot)
    await connection_manager.broadcast(simulation_id, event)
