from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

EdgeStatus = Literal["open", "congested", "closed", "emergency-closed", "recommended"]


@dataclass
class GraphEdge:
    """A directed or bidirectional edge in the venue graph — matches frontend VenueEdge."""
    id: str
    from_node: str      # source node id
    to_node: str        # target node id
    width: float        # walkway width (meters)
    length: float       # edge length (meters)
    base_cost: float    # base routing cost (lower = preferred)
    capacity: int       # max people/min flow

    # Runtime state (mutated during simulation)
    status: EdgeStatus = "open"
    flow: float = 0.0       # current people/min
    density: float = 0.0    # 0..1 fraction of capacity
    current_occupancy: int = 0   # people currently on this edge
    disabled: bool = False       # True = emergency closed

    @property
    def utilization(self) -> float:
        if self.capacity <= 0:
            return 0.0
        return min(1.0, self.flow / self.capacity)

    @property
    def dynamic_cost(self) -> float:
        """Cost adjusted for congestion — used by A* pathfinder."""
        congestion_penalty = self.density * 3.0
        return self.base_cost + congestion_penalty

    @property
    def is_traversable(self) -> bool:
        return not self.disabled and self.status not in ("closed", "emergency-closed")

    def to_frontend_dict(self) -> dict:
        return {
            "id": self.id,
            "from": self.from_node,
            "to": self.to_node,
            "width": self.width,
            "capacity": self.capacity,
            "length": self.length,
            "cost": self.base_cost,
            "status": self.status,
            "flow": round(self.flow, 1),
            "density": round(self.density, 4),
        }
