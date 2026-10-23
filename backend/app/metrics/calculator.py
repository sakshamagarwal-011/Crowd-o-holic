from __future__ import annotations

"""
Crowd metrics calculator.
All calculations are deterministic — never delegated to AI.
Matches frontend CrowdMetrics type exactly.
"""

import math
from typing import Any

from app.simulation.crowd import SimAgent
from app.graph.graph import VenueGraph


def calculate_metrics(
    agents: list[SimAgent],
    graph: VenueGraph,
    scenario: dict[str, Any],
    total_entered: int,
    total_exited: int,
) -> dict[str, Any]:
    """
    Compute all CrowdMetrics. Returns a dict matching frontend CrowdMetrics type.
    """
    active = len(agents)

    # Density — average across non-closed edges
    total_density = 0.0
    n_edges = 0
    for e in graph.edges.values():
        if e.status in ("closed", "emergency-closed"):
            continue
        total_density += e.density
        n_edges += 1
    avg_density = total_density / n_edges if n_edges > 0 else 0.0

    # Flow rate — aggregate of all edge flows
    flow_rate = sum(e.flow for e in graph.edges.values())

    # Average speed — weighted by agent velocity magnitude
    if active > 0:
        total_speed = sum(math.hypot(a.vx, a.vy) * 20 for a in agents)
        avg_speed = total_speed / active
    else:
        avg_speed = 0.0

    # Queue growth — derivative approximation
    queue_growth = max(0.0, active * 0.02) if active > 0 else 0.0

    # Capacity utilization (relative to a 16000-person reference — matches frontend)
    cap_util = min(1.0, active / 16000.0)

    # Per-gate queue lengths
    queue_lengths: dict[str, int] = {}
    entry_dist = scenario.get("entryDistribution", [])
    for dist in entry_dist:
        gate_id = dist["gateId"]
        count_at_gate = sum(1 for a in agents if a.from_node_id == gate_id)
        queue_lengths[gate_id] = round(count_at_gate * 0.3)

    return {
        "peopleCount": active,
        "avgDensity": round(avg_density, 4),
        "flowRate": round(flow_rate, 1),
        "avgSpeed": round(avg_speed, 3),
        "queueGrowth": round(queue_growth, 3),
        "capacityUtilization": round(cap_util, 4),
        "queueLengths": queue_lengths,
    }
