from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

from app.services import simulation_service
from app.services.venue_service import get_venue_for_simulation
from app.services.ai_service import get_ai_provider
from app.simulation.generator import default_scenario_dict
from app.realtime.broadcaster import build_snapshot
from app.core.exceptions import SimulationStateError

router = APIRouter(prefix="/api/simulations", tags=["Simulations"])


class CreateSimulationRequest(BaseModel):
    scenario: dict[str, Any] | None = None
    venue_id: str = "venue-stadium-a"
    seed: int = 42
    simulation_id: str | None = None


class SpeedRequest(BaseModel):
    multiplier: float


@router.post("")
async def create_simulation(req: CreateSimulationRequest):
    scenario = req.scenario or default_scenario_dict()
    graph = get_venue_for_simulation(req.venue_id)
    ai = get_ai_provider()
    engine = simulation_service.create_simulation(
        scenario=scenario,
        graph=graph,
        ai_provider=ai,
        seed=req.seed,
        simulation_id=req.simulation_id,
    )
    return {"simulation_id": engine.simulation_id, "status": engine.state.status}


@router.get("")
async def list_simulations():
    return {"simulation_ids": simulation_service.list_simulations()}


@router.get("/{simulation_id}")
async def get_simulation(simulation_id: str):
    engine = simulation_service.get_simulation(simulation_id)
    return {
        "simulation_id": engine.simulation_id,
        "status": engine.state.status,
        "sim_time_min": round(engine.state.sim_time_min, 2),
        "speed_multiplier": engine.state.speed_multiplier,
        "total_entered": engine.state.total_entered,
        "total_exited": engine.state.total_exited,
    }


@router.post("/{simulation_id}/start")
async def start_simulation(simulation_id: str):
    engine = simulation_service.get_simulation(simulation_id)
    try:
        engine.start()
    except ValueError as e:
        raise SimulationStateError(str(e))
    return {"status": engine.state.status}


@router.post("/{simulation_id}/pause")
async def pause_simulation(simulation_id: str):
    engine = simulation_service.get_simulation(simulation_id)
    try:
        engine.pause()
    except ValueError as e:
        raise SimulationStateError(str(e))
    return {"status": engine.state.status}


@router.post("/{simulation_id}/resume")
async def resume_simulation(simulation_id: str):
    engine = simulation_service.get_simulation(simulation_id)
    try:
        engine.resume()
    except ValueError as e:
        raise SimulationStateError(str(e))
    return {"status": engine.state.status}


@router.post("/{simulation_id}/stop")
async def stop_simulation(simulation_id: str):
    engine = simulation_service.get_simulation(simulation_id)
    engine.stop()
    return {"status": engine.state.status}


@router.post("/{simulation_id}/reset")
async def reset_simulation(simulation_id: str):
    engine = simulation_service.get_simulation(simulation_id)
    engine.reset()
    return {"status": engine.state.status}


@router.post("/{simulation_id}/speed")
async def set_speed(simulation_id: str, req: SpeedRequest):
    engine = simulation_service.get_simulation(simulation_id)
    engine.set_speed(req.multiplier)
    return {"speed_multiplier": engine.state.speed_multiplier}


@router.get("/{simulation_id}/state")
async def get_simulation_state(simulation_id: str):
    engine = simulation_service.get_simulation(simulation_id)
    metrics, safety = engine.get_snapshot_data()
    snapshot = build_snapshot(engine.state, engine.graph, metrics, safety)
    return snapshot


class ApplyScenarioRequest(BaseModel):
    scenario: dict[str, Any]


@router.post("/{simulation_id}/scenario")
async def apply_scenario(simulation_id: str, req: ApplyScenarioRequest):
    engine = simulation_service.get_simulation(simulation_id)
    engine.set_scenario(req.scenario)
    metrics, safety = engine.get_snapshot_data()
    from app.realtime.broadcaster import broadcast_snapshot
    await broadcast_snapshot(simulation_id, engine.state, engine.graph, metrics, safety)
    return {
        "status": engine.state.status,
        "scenario_id": engine.state.scenario_id,
        "crowd_size": engine.state.scenario.get("crowdSize"),
        "incidents_count": len(engine.state.scenario.get("incidents", [])),
    }
