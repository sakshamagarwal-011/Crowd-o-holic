from __future__ import annotations

"""
Simulation Engine — the core product loop.
Runs the deterministic simulation in an asyncio background task.
Completely independent from HTTP and WebSocket code.

Pipeline per tick:
  spawn agents → move agents → update edge metrics →
  compute crowd metrics → compute safety/risk →
  update routing → maybe trigger AI analysis →
  broadcast snapshot
"""

import asyncio
import random
import time
import uuid
from typing import Any, TYPE_CHECKING

from app.simulation.state import SimulationRuntimeState
from app.simulation.crowd import CrowdGroup, SimAgent
from app.simulation.generator import generate_crowd_groups
from app.simulation.movement import spawn_agents, move_agents, update_edge_metrics
from app.simulation.queues import compute_queue_states
from app.metrics.calculator import calculate_metrics
from app.risk.engine import compute_safety_state
from app.routing.dynamic_router import (
    build_default_routes, recompute_routes, update_route_flows
)
from app.realtime.broadcaster import broadcast_snapshot
from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.graph.graph import VenueGraph
    from app.ai.provider import AIProvider

log = get_logger(__name__)


class SimulationEngine:
    """
    Manages one simulation lifecycle.
    Created fresh per simulation run.
    """

    def __init__(
        self,
        simulation_id: str,
        scenario: dict[str, Any],
        graph: VenueGraph,
        ai_provider: AIProvider,
        seed: int = 42,
    ):
        self.simulation_id = simulation_id
        self.graph = graph
        self.ai_provider = ai_provider
        self.seed = seed

        rng = random.Random(seed)
        groups = generate_crowd_groups(scenario, seed=seed)

        self.state = SimulationRuntimeState(
            simulation_id=simulation_id,
            scenario_id=scenario.get("id", "unknown"),
            venue_id=scenario.get("venueId", "venue-stadium-a"),
            seed=seed,
            scenario=scenario,
            groups=groups,
        )

        # Reset graph runtime state
        graph.reset_edge_flows()
        graph.reset_node_occupancy()

        # Build default routes
        self.state.routes = build_default_routes(graph)

        # Apply validated scenario incidents and observations
        from app.emergency.manager import apply_scenario_incidents
        apply_scenario_incidents(self.state, self.graph, scenario.get("incidents", []))

        # Initial edge metrics update
        update_edge_metrics(self.state.agents, self.graph, self.state.edge_density_offsets)

        self.state.push_timeline("simulation", "Simulation created", "Awaiting start command.")

        self._rng = rng
        self._task: asyncio.Task | None = None
        self._ai_task: asyncio.Task | None = None

        log.info(
            "SimulationEngine created | id=%s scenario=%s groups=%d seed=%d",
            simulation_id, scenario.get("id"), len(groups), seed,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self.state.status not in ("created", "stopped", "completed", "failed"):
            raise ValueError(f"Cannot start from state '{self.state.status}'")
        if self.state.status in ("stopped", "completed", "failed"):
            self._reset_state()
        self.state.status = "running"
        self.state.started_at = time.time()
        self.state.push_timeline("simulation", "Simulation started", "Live crowd simulation running.")
        log.info("Simulation started | id=%s", self.simulation_id)
        self._task = asyncio.create_task(self._run_loop())

    def pause(self) -> None:
        if self.state.status != "running":
            raise ValueError(f"Cannot pause from state '{self.state.status}'")
        self.state.status = "paused"
        self.state.push_timeline("simulation", "Simulation paused", "Operator paused the simulation.")
        log.info("Simulation paused | id=%s", self.simulation_id)

    def resume(self) -> None:
        if self.state.status != "paused":
            raise ValueError(f"Cannot resume from state '{self.state.status}'")
        self.state.status = "running"
        self.state.push_timeline("simulation", "Simulation resumed", "Operator resumed the simulation.")
        log.info("Simulation resumed | id=%s", self.simulation_id)

    def stop(self) -> None:
        self.state.status = "stopped"
        self.state.ended_at = time.time()
        if self._task:
            self._task.cancel()
        self.state.push_timeline("simulation", "Simulation stopped", "Operator stopped the simulation.")
        log.info("Simulation stopped | id=%s", self.simulation_id)

    def reset(self) -> None:
        if self._task:
            self._task.cancel()
        self._reset_state()
        log.info("Simulation reset | id=%s", self.simulation_id)

    def set_speed(self, multiplier: float) -> None:
        self.state.speed_multiplier = max(0.1, min(20.0, multiplier))

    def set_scenario(self, scenario: dict[str, Any]) -> None:
        """Update active scenario configuration and reinitialize simulation state."""
        if self._task and not self._task.done():
            self._task.cancel()
        self.state.scenario = scenario
        self.state.scenario_id = scenario.get("id", self.state.scenario_id)
        self.state.venue_id = scenario.get("venueId", self.state.venue_id)
        self._reset_state()
        self.state.push_timeline(
            "scenario",
            f"Scenario configured: {scenario.get('name', 'Event')}",
            f"{scenario.get('crowdSize', 0):,} attendees · {len(scenario.get('incidents', []))} incident(s) active.",
        )
        log.info(
            "Simulation scenario updated | id=%s crowd_size=%d",
            self.simulation_id, scenario.get("crowdSize", 0),
        )

    def _reset_state(self) -> None:
        groups = generate_crowd_groups(self.state.scenario, seed=self.seed)
        self.state.status = "created"
        self.state.sim_time_min = -60.0
        self.state.agents = []
        self.state.groups = groups
        self.state.next_agent_id = [0]
        self.state.total_entered = 0
        self.state.total_exited = 0
        self.state.path_cache = {}
        self.state.emergency = None
        self.state.disabled_edges = set()
        self.state.restricted_edges.clear()
        self.state.edge_density_offsets.clear()
        self.state.routes = build_default_routes(self.graph)
        self.state.route_changes = []
        self.state.timeline = []
        self.state.ai_history = []
        self.state.ai_current = None
        self.state.ai_stage = "idle"
        self.state.last_ai_sim_minute = -999.0
        self.state.bottleneck_ticks = {}
        self.state.acknowledged_alerts = set()
        self.graph.reset_edge_flows()
        self.graph.reset_node_occupancy()

        # Re-apply scenario incidents & observations
        from app.emergency.manager import apply_scenario_incidents
        apply_scenario_incidents(self.state, self.graph, self.state.scenario.get("incidents", []))
        update_edge_metrics(self.state.agents, self.graph, self.state.edge_density_offsets)

        self._rng = random.Random(self.seed)
        self.state.push_timeline("simulation", "Simulation reset", "State cleared and scenario initialized.")

    # ── Main simulation loop ──────────────────────────────────────────────────

    async def _run_loop(self) -> None:
        tick_interval = 1.0 / settings.realtime_update_hz
        dt_sec = settings.simulation_timestep

        try:
            while self.state.status in ("running", "paused"):
                t_start = time.monotonic()

                if self.state.status == "running":
                    await self._tick(dt_sec)

                    # Check simulation completion
                    timing = self.state.scenario.get("timing", {})
                    max_dur = float(timing.get("durationMin", settings.max_simulation_duration))
                    if self.state.sim_time_min >= max_dur:
                        self.state.status = "completed"
                        self.state.ended_at = time.time()
                        self.state.push_timeline(
                            "simulation",
                            "Simulation completed",
                            f"Event concluded. {self.state.total_exited:,} people exited.",
                        )
                        log.info("Simulation completed | id=%s exited=%d",
                                 self.simulation_id, self.state.total_exited)
                        break

                # Broadcast even when paused (for initial state)
                metrics, safety = self._compute_state()
                await broadcast_snapshot(
                    self.simulation_id, self.state, self.graph, metrics, safety
                )

                elapsed = time.monotonic() - t_start
                sleep_time = max(0.0, tick_interval / max(self.state.speed_multiplier, 0.5) - elapsed)
                # Use fixed interval for broadcast rate regardless of speed
                sleep_time = max(0.0, tick_interval - elapsed)
                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            log.info("Simulation loop cancelled | id=%s", self.simulation_id)
        except Exception as e:
            log.exception("Simulation loop error | id=%s error=%s", self.simulation_id, e)
            self.state.status = "failed"

        # Final broadcast
        metrics, safety = self._compute_state()
        await broadcast_snapshot(self.simulation_id, self.state, self.graph, metrics, safety)

    async def _tick(self, dt_sec: float) -> None:
        """One simulation tick."""
        speed = self.state.speed_multiplier
        effective_dt = dt_sec * speed

        # Advance simulation time
        self.state.sim_time_min += effective_dt / 60.0

        # Spawn new agents
        spawned = spawn_agents(
            self.state.groups,
            self.state.sim_time_min,
            effective_dt,
            1.0,   # speed_mult already applied to dt
            self.graph,
            self.state.agents,
            self.state.next_agent_id,
            self._rng,
            self.state.path_cache,
            restricted_edges=self.state.restricted_edges,
            disabled_edges=self.state.disabled_edges,
        )
        self.state.total_entered += spawned

        # Move agents
        remaining, exited = move_agents(
            self.state.agents,
            effective_dt,
            1.0,
            self.graph,
            self.state.groups,
            self._rng,
            self.state.path_cache,
            restricted_edges=self.state.restricted_edges,
            disabled_edges=self.state.disabled_edges,
        )
        self.state.agents = remaining
        self.state.total_exited += exited

        # Update edge metrics
        update_edge_metrics(self.state.agents, self.graph, edge_density_offsets=self.state.edge_density_offsets)

        # Update route flows
        update_route_flows(self.state.routes, self.graph)

        # Maybe trigger AI analysis (async, non-blocking)
        self._maybe_trigger_ai()

    def _compute_state(self) -> tuple[dict, dict]:
        """Compute metrics and safety state synchronously."""
        metrics = calculate_metrics(
            self.state.agents,
            self.graph,
            self.state.scenario,
            self.state.total_entered,
            self.state.total_exited,
        )
        safety = compute_safety_state(
            self.graph,
            metrics,
            self.state.bottleneck_ticks,
            self.state.acknowledged_alerts,
            self.state.emergency,
            self.state.sim_time_min,
        )
        return metrics, safety

    # ── AI integration ────────────────────────────────────────────────────────

    def _maybe_trigger_ai(self) -> None:
        """Trigger AI analysis if conditions warrant it (async, non-blocking)."""
        if self._ai_task and not self._ai_task.done():
            return  # AI already running

        metrics, safety = self._compute_state()
        risk_level = safety.get("riskLevel", "low")
        bottlenecks = safety.get("bottlenecks", [])

        should_analyze = (
            (self.state.emergency and self.state.emergency.active)
            or any(bn["risk"] in ("critical", "high") for bn in bottlenecks)
            or (self.state.sim_time_min - self.state.last_ai_sim_minute >= 30)
        )

        cooldown_ok = (
            self.state.sim_time_min - self.state.last_ai_sim_minute
            >= settings.ai_cooldown_sim_minutes
        )

        if should_analyze and cooldown_ok:
            self.state.last_ai_sim_minute = self.state.sim_time_min
            self.state.ai_stage = "analyzing"
            self._ai_task = asyncio.create_task(
                self._run_ai_analysis(metrics, safety)
            )

    async def _run_ai_analysis(self, metrics: dict, safety: dict) -> None:
        """Run AI safety analysis asynchronously. Simulation continues regardless."""
        try:
            em_dict = self.state.emergency.to_frontend_dict() if self.state.emergency else None
            rc_dicts = [rc.to_frontend_dict() for rc in self.state.route_changes[:3]]

            analysis = await self.ai_provider.analyze_safety(
                metrics=metrics,
                safety_state=safety,
                sim_time_min=self.state.sim_time_min,
                sim_status=self.state.status,
                emergency=em_dict,
                route_changes=rc_dicts,
            )

            # Convert to frontend AIRecommendation format
            rec = {
                "id": f"ai-{int(time.time())}",
                "atMinute": round(self.state.sim_time_min, 2),
                "riskLevel": analysis.urgency,
                "headline": analysis.summary,
                "explanation": analysis.risk_explanation,
                "recommendedAction": analysis.recommended_action,
                "confidence": analysis.confidence,
                "basis": f"Risk score {safety.get('riskScore', 0)}/100, {len(safety.get('bottlenecks', []))} bottleneck(s).",
            }
            self.state.ai_current = rec
            self.state.ai_history.insert(0, rec)
            if len(self.state.ai_history) > 8:
                self.state.ai_history = self.state.ai_history[:8]

            self.state.ai_stage = "complete"
            self.state.push_timeline(
                "ai-recommendation",
                "AI Safety analysis updated",
                analysis.summary,
                severity=analysis.urgency,
            )
            log.info("AI analysis complete | urgency=%s sim=%s", analysis.urgency, self.simulation_id)

        except Exception as e:
            log.warning("AI analysis failed | sim=%s error=%s", self.simulation_id, type(e).__name__)
            self.state.ai_stage = "idle"
            # Simulation continues normally

    # ── Public state access ───────────────────────────────────────────────────

    def get_snapshot_data(self) -> tuple[dict, dict]:
        """Get current metrics and safety state for snapshot building."""
        return self._compute_state()

    def acknowledge_alert(self, alert_id: str) -> None:
        self.state.acknowledged_alerts.add(alert_id)
