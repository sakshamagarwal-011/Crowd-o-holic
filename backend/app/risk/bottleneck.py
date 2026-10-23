from __future__ import annotations

"""
Deterministic bottleneck detection and prediction.
Uses actual simulation metrics — no AI involved.
Implements hysteresis (persistence ticks) to avoid noisy triggers.
"""

import time
from typing import Any

from app.graph.graph import VenueGraph
from app.graph.edges import GraphEdge
from app.risk.thresholds import THRESHOLDS


def detect_bottlenecks(
    graph: VenueGraph,
    metrics: dict[str, Any],
    bottleneck_ticks: dict[str, int],
    sim_time_min: float,
) -> tuple[list[dict], list[dict]]:
    """
    Detect confirmed and predicted bottlenecks.
    Returns (bottlenecks, predicted_bottlenecks) — dicts matching frontend Bottleneck type.
    bottleneck_ticks: mutable dict tracking how long each edge has been congested.
    """
    bottlenecks: list[dict] = []
    predicted: list[dict] = []

    for edge in graph.edges.values():
        if edge.status in ("closed", "emergency-closed"):
            bottleneck_ticks.pop(edge.id, None)
            continue

        if edge.density < THRESHOLDS.bottleneck_density:
            bottleneck_ticks.pop(edge.id, None)
            continue

        # Increment persistence counter
        bottleneck_ticks[edge.id] = bottleneck_ticks.get(edge.id, 0) + 1

        if bottleneck_ticks[edge.id] < THRESHOLDS.bottleneck_persistence:
            # Building up — may become predicted
            if edge.density > THRESHOLDS.bottleneck_density * 0.85:
                pred = _make_bottleneck(edge, graph, sim_time_min, predicted=True)
                if pred:
                    predicted.append(pred)
            continue

        # Confirmed bottleneck
        bn = _make_bottleneck(edge, graph, sim_time_min, predicted=False)
        if bn:
            bottlenecks.append(bn)

    # Sort by density descending
    bottlenecks.sort(key=lambda b: b["currentDensity"], reverse=True)
    predicted.sort(key=lambda b: b["currentDensity"], reverse=True)

    return bottlenecks[:6], predicted[:3]


def _make_bottleneck(
    edge: GraphEdge,
    graph: VenueGraph,
    sim_time_min: float,
    predicted: bool = False,
) -> dict | None:
    to_node = graph.get_node(edge.to_node)
    if to_node is None:
        return None

    density = edge.density
    cap_util = min(1.0, edge.flow / max(edge.capacity, 1))

    # Risk level from density
    if density >= THRESHOLDS.density_emergency:
        risk = "emergency"
    elif density >= THRESHOLDS.density_critical:
        risk = "critical"
    elif density >= THRESHOLDS.density_high:
        risk = "high"
    elif density >= THRESHOLDS.density_moderate:
        risk = "moderate"
    else:
        risk = "low"

    # Time-to-critical estimation (deterministic)
    ttc = _estimate_time_to_critical(edge, density, sim_time_min)

    # Find redirect suggestion
    redirect_action, redirect_edge_id = _find_redirect(edge, graph)

    prefix = "pred-" if predicted else ""
    return {
        "id": f"{prefix}bn-{edge.id}",
        "edgeId": edge.id,
        "nodeLabel": to_node.label,
        "location": to_node.label,
        "currentDensity": round(density, 4),
        "capacityUtilization": round(cap_util, 4),
        "risk": risk,
        "timeToCriticalMin": ttc,
        "predictedEscalation": density > THRESHOLDS.density_high * 0.9 and density < THRESHOLDS.density_critical,
        "recommendedAction": redirect_action,
        "redirectToEdgeId": redirect_edge_id,
    }


def _estimate_time_to_critical(
    edge: GraphEdge, density: float, sim_time_min: float
) -> float | None:
    """
    Deterministic estimate of minutes until density reaches critical threshold.
    Based on current density gradient (simplified linear model).
    Returns None if unreliable.
    """
    if density < THRESHOLDS.density_high:
        return None
    if density >= THRESHOLDS.density_critical:
        return max(1.0, round((1.0 - density) * 30.0, 1))

    # Interpolate: how fast is density growing based on flow vs capacity?
    flow_ratio = edge.flow / max(edge.capacity, 1)
    if flow_ratio <= 0.5:
        return None

    # Simple linear estimate
    headroom = THRESHOLDS.density_critical - density
    growth_rate = (flow_ratio - 0.5) * 0.05  # density units per sim-minute
    if growth_rate <= 0:
        return None

    return round(headroom / growth_rate, 1)


def _find_redirect(
    edge: GraphEdge, graph: VenueGraph
) -> tuple[str, str | None]:
    """Find the best alternative less-congested edge from the same from-node."""
    candidates: list[GraphEdge] = []
    for _neighbor, eid in graph.neighbors(edge.from_node):
        e = graph.get_edge(eid)
        if e and e.id != edge.id and e.is_traversable:
            candidates.append(e)

    if not candidates:
        return "Monitor and prepare to redirect flow.", None

    # Pick the least congested corridor with the most remaining capacity
    candidates.sort(key=lambda c: (c.density, -c.capacity))
    best = candidates[0]

    if best.density < 0.70:
        to_node = graph.get_node(best.to_node)
        label = to_node.label if to_node else best.to_node
        return f"Redirect incoming crowd toward {label}.", best.id

    return "Monitor and prepare to redirect flow.", None

