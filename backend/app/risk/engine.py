from __future__ import annotations

"""
Deterministic risk engine.
Computes risk score and level from simulation state.
Never calls AI — AI explains the results, not calculates them.
Matches frontend SafetyState type.
"""

import time
from typing import Any

from app.risk.thresholds import THRESHOLDS
from app.risk.bottleneck import detect_bottlenecks
from app.graph.graph import VenueGraph
from app.simulation.state import EmergencyRecord


def compute_safety_state(
    graph: VenueGraph,
    metrics: dict[str, Any],
    bottleneck_ticks: dict[str, int],
    acknowledged_alerts: set[str],
    emergency: EmergencyRecord | None,
    sim_time_min: float,
    restricted_edges: dict[str, float] | None = None,
    disabled_edges: set[str] | None = None,
) -> dict[str, Any]:
    """
    Compute full SafetyState dict matching frontend SafetyState type.
    Dynamically minimizes risk when operator diverts routes, meters inflows,
    or opens relief bypass exits.
    """
    bottlenecks, predicted = detect_bottlenecks(
        graph, metrics, bottleneck_ticks, sim_time_min
    )

    avg_density = float(metrics.get("avgDensity", 0.0))
    peak_density = float(metrics.get("peakDensity", 0.0))
    cap_util = float(metrics.get("capacityUtilization", 0.0))

    restr_set = set(restricted_edges.keys()) if restricted_edges else set()
    dis_set = set(disabled_edges) if disabled_edges else set()

    # 1. Bottlenecks contribution:
    # Corridors actively metered or restricted by the operator have regulated inflow,
    # so we discount their unmitigated stampede severity.
    if bottlenecks:
        unmitigated_bns = [b for b in bottlenecks if b.get("edgeId") not in restr_set]
        if unmitigated_bns:
            worst_density = unmitigated_bns[0]["currentDensity"]
            worst_util = unmitigated_bns[0].get("capacityUtilization", 0.0)
            bn_severity = max(worst_density, worst_util)
        else:
            # All bottlenecks are actively under operator mitigation
            worst_density = bottlenecks[0]["currentDensity"] * 0.4
            worst_util = bottlenecks[0].get("capacityUtilization", 0.0) * 0.4
            bn_severity = max(worst_density, worst_util)

        # Composite load: 45% bottleneck severity, 35% average density, 20% capacity
        base_score = (bn_severity * 0.45 + avg_density * 0.35 + min(1.0, cap_util * 2.5) * 0.20) * 100.0
    else:
        effective_load = max(avg_density, peak_density * 0.75, cap_util * 0.5)
        base_score = effective_load * 100.0

    # 2. Emergency baseline & containment evaluation
    is_emergency_active = bool(emergency and emergency.active)

    # 3. Dynamic Mitigation & Route Diversion Relief Discount:
    # When the operator diverts traffic, meters turnstiles, or opens bypass exits,
    # the risk score minimizes dynamically.
    mitigation_discount = 0.0

    # Credit for active corridor restrictions/metering (diversions in place)
    if restr_set:
        mitigation_discount += min(35.0, len(restr_set) * 12.0)

    # Credit for active relief exit flow (agents moving towards evacuation exits)
    relief_flow = sum(
        e.flow for e in graph.edges.values()
        if e.to_node in ("exit-se", "exit-sw", "exit-n") and e.flow > 0
    )
    if relief_flow > 0:
        mitigation_discount += min(20.0, relief_flow * 0.05)

    # Minimized composite risk score
    risk_score = min(100, max(5, round(base_score - mitigation_discount)))

    # Determine risk level from minimized score and containment status
    if is_emergency_active and not (dis_set and restr_set):
        risk_level = "emergency"
    elif risk_score >= 80:
        risk_level = "critical"
    elif risk_score >= 55:
        risk_level = "high"
    elif risk_score >= 30:
        risk_level = "moderate"
    else:
        risk_level = "low"


    # Time-to-critical: worst confirmed bottleneck
    ttc = None
    for bn in bottlenecks:
        if bn.get("timeToCriticalMin") is not None:
            ttc = bn["timeToCriticalMin"]
            break

    # Build alerts
    alerts = _build_alerts(bottlenecks, emergency, acknowledged_alerts, sim_time_min)

    return {
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "bottlenecks": bottlenecks,
        "predictedBottlenecks": predicted,
        "timeToCriticalMin": ttc,
        "alerts": alerts,
    }


def _build_alerts(
    bottlenecks: list[dict],
    emergency: EmergencyRecord | None,
    acknowledged_alerts: set[str],
    sim_time_min: float,
) -> list[dict]:
    alerts = []

    # Emergency alert first
    if emergency and emergency.active:
        em_key = f"alert-em-{emergency.id}"
        if em_key not in acknowledged_alerts:
            alerts.append({
                "id": em_key,
                "severity": "emergency",
                "title": f"EMERGENCY: {emergency.location}",
                "message": emergency.summary,
                "atMinute": round(emergency.at_minute, 2),
                "acknowledged": False,
            })

    # Bottleneck alerts
    for bn in bottlenecks[:3]:
        key = f"alert-{bn['edgeId']}"
        if key not in acknowledged_alerts:
            pct = round(bn["capacityUtilization"] * 100)
            alerts.append({
                "id": key,
                "severity": bn["risk"],
                "title": f"Bottleneck: {bn['location']}",
                "message": f"{bn['location']} at {pct}% capacity. {bn['recommendedAction']}",
                "atMinute": round(sim_time_min, 2),
                "acknowledged": False,
            })

    return alerts
