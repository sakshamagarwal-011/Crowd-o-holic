from __future__ import annotations

"""
Simulation lifecycle state.
"""

from dataclasses import dataclass, field
from typing import Literal, Any
from datetime import datetime
import time

from app.simulation.crowd import CrowdGroup, SimAgent
from app.graph.graph import VenueGraph

SimulationStatus = Literal["created", "running", "paused", "stopped", "completed", "failed"]


@dataclass
class EmergencyRecord:
    id: str
    type: str
    location: str
    node_id: str
    at_minute: float
    active: bool
    closed_edge_ids: list[str]
    summary: str

    def to_frontend_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "location": self.location,
            "nodeId": self.node_id,
            "atMinute": round(self.at_minute, 2),
            "active": self.active,
            "closedEdgeIds": self.closed_edge_ids,
            "summary": self.summary,
        }


@dataclass
class RouteRecord:
    id: str
    from_node_id: str
    to_node_id: str
    segments: list[dict]   # [{edgeId, fromNodeId, toNodeId}]
    status: str
    cost: float
    flow: float
    label: str

    def to_frontend_dict(self) -> dict:
        return {
            "id": self.id,
            "fromNodeId": self.from_node_id,
            "toNodeId": self.to_node_id,
            "segments": self.segments,
            "status": self.status,
            "cost": round(self.cost, 3),
            "flow": round(self.flow, 1),
            "label": self.label,
        }


@dataclass
class RouteChangeRecord:
    id: str
    at_minute: float
    reason: str
    from_route_id: str
    to_route_id: str
    affected_edge_id: str
    redistributed_flow: float

    def to_frontend_dict(self) -> dict:
        return {
            "id": self.id,
            "atMinute": round(self.at_minute, 2),
            "reason": self.reason,
            "fromRouteId": self.from_route_id,
            "toRouteId": self.to_route_id,
            "affectedEdgeId": self.affected_edge_id,
            "redistributedFlow": round(self.redistributed_flow, 1),
        }


@dataclass
class TimelineEntry:
    id: str
    at_minute: float
    kind: str
    title: str
    detail: str
    severity: str | None = None

    def to_frontend_dict(self) -> dict:
        d = {
            "id": self.id,
            "atMinute": round(self.at_minute, 2),
            "kind": self.kind,
            "title": self.title,
            "detail": self.detail,
        }
        if self.severity:
            d["severity"] = self.severity
        return d


@dataclass
class SimulationRuntimeState:
    """All mutable state for one active simulation."""
    simulation_id: str
    scenario_id: str
    venue_id: str
    seed: int
    status: SimulationStatus = "created"

    sim_time_min: float = -60.0         # starts 60 min before event
    speed_multiplier: float = 1.0

    agents: list[SimAgent] = field(default_factory=list)
    groups: list[CrowdGroup] = field(default_factory=list)
    next_agent_id: list[int] = field(default_factory=lambda: [0])

    total_entered: int = 0
    total_exited: int = 0

    # Scenario dict (raw, for metrics/queue calcs)
    scenario: dict = field(default_factory=dict)

    # Path cache for A* (reset on emergency)
    path_cache: dict = field(default_factory=dict)

    # Emergency state
    emergency: EmergencyRecord | None = None

    # Routing state
    routes: list[RouteRecord] = field(default_factory=list)
    route_changes: list[RouteChangeRecord] = field(default_factory=list)
    disabled_edges: set[str] = field(default_factory=set)
    restricted_edges: dict[str, float] = field(default_factory=dict)  # edge_id -> slowdown factor (e.g. 0.35)
    edge_density_offsets: dict[str, float] = field(default_factory=dict)  # edge_id -> baseline density offset

    # Active incidents & observations
    incidents: list[dict] = field(default_factory=list)
    unresolved_locations: list[str] = field(default_factory=list)
    medical_routes: list[RouteRecord] = field(default_factory=list)

    # Timeline
    timeline: list[TimelineEntry] = field(default_factory=list)

    # AI state
    ai_history: list[dict] = field(default_factory=list)
    ai_current: dict | None = None
    ai_stage: str = "idle"
    last_ai_sim_minute: float = -999.0

    # Bottleneck tracking (for hysteresis)
    bottleneck_ticks: dict[str, int] = field(default_factory=dict)
    acknowledged_alerts: set[str] = field(default_factory=set)

    # Route change cooldown
    last_route_change_minute: float = -999.0

    # Timestamps
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    ended_at: float | None = None

    def push_timeline(
        self, kind: str, title: str, detail: str, severity: str | None = None
    ) -> None:
        import time as t
        entry = TimelineEntry(
            id=f"tl-{t.time_ns()}-{kind[:3]}",
            at_minute=self.sim_time_min,
            kind=kind,
            title=title,
            detail=detail,
            severity=severity,
        )
        self.timeline.insert(0, entry)
        if len(self.timeline) > 50:
            self.timeline = self.timeline[:50]
