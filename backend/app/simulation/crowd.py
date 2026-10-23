from __future__ import annotations

"""
Crowd group and agent data models.
We use aggregated flow groups rather than individual agents for scalability.
The frontend expects individual SimAgent objects for rendering (up to MAX_AGENTS_RENDERED).
Each CrowdGroup tracks its flow aggregate; agents are generated for visualization.
"""

from dataclasses import dataclass, field
from typing import Literal
import uuid

AgentState = Literal["waiting", "moving", "queued", "arrived", "exited", "rerouting"]


@dataclass
class CrowdGroup:
    """
    A group of people with shared origin, destination, and timing.
    Matches frontend CrowdGroup type.
    """
    id: str
    name: str
    total_size: int
    entry_gate_id: str
    destination_node_id: str
    arrival_start_min: float    # sim-minutes from t=0
    arrival_end_min: float

    # Runtime
    spawned: int = 0            # how many have been spawned
    active: int = 0             # currently in simulation
    exited: int = 0             # reached destination

    @property
    def remaining_to_spawn(self) -> int:
        return max(0, self.total_size - self.spawned)

    @property
    def arrival_window_min(self) -> float:
        return max(1.0, self.arrival_end_min - self.arrival_start_min)

    def spawn_rate_per_min(self) -> float:
        """People per sim-minute this group should spawn during its window."""
        return self.total_size / self.arrival_window_min


@dataclass
class SimAgent:
    """
    A single simulated person — used for frontend visualization.
    Matches frontend SimAgent type.
    """
    id: int
    x: float
    y: float
    vx: float
    vy: float
    group_id: str
    from_node_id: str
    to_node_id: str
    edge_id: str
    progress: float     # 0..1 along current edge
    speed: float        # logical units / real-second

    state: AgentState = "moving"
    destination_node_id: str = ""

    def to_frontend_dict(self) -> dict:
        return {
            "id": self.id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "vx": round(self.vx, 3),
            "vy": round(self.vy, 3),
            "groupId": self.group_id,
            "fromNodeId": self.from_node_id,
            "toNodeId": self.to_node_id,
            "edgeId": self.edge_id,
            "progress": round(self.progress, 4),
            "speed": round(self.speed, 2),
        }
