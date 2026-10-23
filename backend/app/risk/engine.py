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
) -> dict[str, Any]:
    """
    Compute full SafetyState dict matching frontend SafetyState type.
    """
    bottlenecks, predicted = detect_bottlenecks(
        graph, metrics, bottleneck_ticks, sim_time_min
    )

    # Risk score: derived deterministically from worst bottleneck or peak/average venue load
    if bottlenecks:
        max_density = bottlenecks[0]["currentDensity"]
        max_util = bottlenecks[0].get("capacityUtilization", 0.0)
        risk_score = min(100, max(0, round(max(max_density, max_util) * 100)))
    else:
        avg_density = float(metrics.get("avgDensity", 0.0))
        peak_density = float(metrics.get("peakDensity", 0.0))
        peak_util = float(metrics.get("capacityUtilization", 0.0))
        # Composite physical stress without arbitrary inflation
        effective_load = max(avg_density, peak_density * 0.8, peak_util * 0.7)
        risk_score = min(100, max(0, round(effective_load * 100)))

    # Risk level: separate emergency severity classification from numerical score
    if emergency and emergency.active:
        risk_level = "emergency"
    elif risk_score >= 85:
        risk_level = "critical"
    elif risk_score >= 60:
        risk_level = "high"
    elif risk_score >= 35:
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
