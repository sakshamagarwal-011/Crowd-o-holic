from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

NodeKind = Literal["entry", "exit", "junction", "facility", "stage", "medical", "food"]


@dataclass
class GraphNode:
    """A node in the venue graph — matches frontend VenueNode type."""
    id: str
    label: str
    kind: NodeKind
    x: float            # canvas-space (0..1000 logical units)
    y: float            # canvas-space (0..620 logical units)
    capacity: int       # max occupancy
    description: str = ""

    # Runtime state (mutated during simulation)
    current_occupancy: int = 0

    @property
    def utilization(self) -> float:
        if self.capacity <= 0:
            return 0.0
        return min(1.0, self.current_occupancy / self.capacity)

    def to_frontend_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "x": self.x,
            "y": self.y,
            "capacity": self.capacity,
            "description": self.description,
        }
