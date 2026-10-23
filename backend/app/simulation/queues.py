from __future__ import annotations

"""
Queue tracking for the simulation.
Queues form when inflow to a node exceeds its service/exit rate.
Queue growth feeds the risk engine.
"""

from dataclasses import dataclass, field


@dataclass
class QueueState:
    """Runtime queue state at a node or edge."""
    location_id: str        # node or edge id
    label: str
    queue_size: int = 0
    growth_rate: float = 0.0    # people/sim-minute
    service_rate: float = 0.0   # people/sim-minute
    capacity: int = 0
    is_saturated: bool = False

    @property
    def saturation_ratio(self) -> float:
        if self.capacity <= 0:
            return 0.0
        return min(1.0, self.queue_size / self.capacity)


def compute_queue_states(
    agents_per_gate: dict[str, int],
    scenario: dict,
) -> dict[str, QueueState]:
    """
    Compute queue states at entry gates.
    agents_per_gate: {gate_id: count_of_agents_at_gate}
    """
    queues: dict[str, QueueState] = {}
    entry_dist = scenario.get("entryDistribution", [])
    entry_rate = float(scenario.get("entryRate", 600))

    for dist in entry_dist:
        gate_id = dist["gateId"]
        fraction = float(dist.get("fraction", 1.0))
        gate_capacity_per_min = entry_rate * fraction
        count = agents_per_gate.get(gate_id, 0)

        growth = max(0.0, count * 0.02 - gate_capacity_per_min * 0.1)
        is_sat = count > gate_capacity_per_min * 0.8

        queues[gate_id] = QueueState(
            location_id=gate_id,
            label=gate_id,
            queue_size=round(count * 0.3),
            growth_rate=round(growth, 2),
            service_rate=gate_capacity_per_min,
            capacity=int(gate_capacity_per_min),
            is_saturated=is_sat,
        )

    return queues
