from __future__ import annotations

"""
Deterministic crowd generator.
Creates CrowdGroup objects from scenario parameters.
Uses a seeded random for reproducible simulations.
"""

import random
from typing import Any

from app.simulation.crowd import CrowdGroup


def generate_crowd_groups(
    scenario: dict[str, Any],
    seed: int = 42,
) -> list[CrowdGroup]:
    """
    Build CrowdGroup list from a scenario dict.
    Scenario dict fields (matches frontend Scenario type):
      - crowdGroups: list of group dicts
      - crowdSize: int
      - entryDistribution: list of {gateId, fraction}
      - timing: {startMinutesOfDay, durationMin, arrivalPattern, departurePattern}
    """
    rng = random.Random(seed)

    crowd_size = scenario.get("crowdSize", 10000)

    # If explicit crowdGroups provided, scale proportionally to match scenario crowdSize
    if scenario.get("crowdGroups"):
        groups: list[CrowdGroup] = []
        raw_groups = scenario["crowdGroups"]
        raw_total = sum(g.get("size", 0) for g in raw_groups)
        scale = (crowd_size / raw_total) if raw_total > 0 else 1.0
        allocated = 0
        for i, g in enumerate(raw_groups):
            g_size = int(g["size"] * scale) if i < len(raw_groups) - 1 else (crowd_size - allocated)
            allocated += g_size
            groups.append(CrowdGroup(
                id=g["id"],
                name=g.get("name", g["id"]),
                total_size=max(1, g_size),
                entry_gate_id=g["entryGateId"],
                destination_node_id=g["destinationNodeId"],
                arrival_start_min=float(g.get("arrivalStartMin", -60)),
                arrival_end_min=float(g.get("arrivalEndMin", 0)),
            ))
        return groups

    # Otherwise, auto-generate from distribution
    entry_dist = scenario.get("entryDistribution", [])
    timing = scenario.get("timing", {})
    arrival_pattern = timing.get("arrivalPattern", "surge")
    duration = float(timing.get("durationMin", 180))

    if not entry_dist:
        entry_dist = [
            {"gateId": "gate-e", "fraction": 0.55},
            {"gateId": "gate-w", "fraction": 0.30},
            {"gateId": "gate-s", "fraction": 0.15},
        ]

    # Check if scenario is a post-event departure/egress
    is_egress = any(
        w in (str(scenario.get("naturalLanguage", "")) + " " + str(scenario.get("name", ""))).lower()
        for w in ["leaving", "depart", "egress", "ended", "evacuat"]
    )
    if is_egress:
        start_min = -60.0
        end_min = 0.0
        w_size = int(crowd_size * 0.45)
        n_size = int(crowd_size * 0.35)
        s_size = crowd_size - w_size - n_size
        return [
            CrowdGroup(
                id="g-egress-west",
                name="West Zone Egress toward Main Gate",
                total_size=w_size,
                entry_gate_id="gate-w",
                destination_node_id="gate-e",
                arrival_start_min=start_min,
                arrival_end_min=end_min,
            ),
            CrowdGroup(
                id="g-egress-north",
                name="North Zone Egress toward Main Gate",
                total_size=n_size,
                entry_gate_id="j-n",
                destination_node_id="gate-e",
                arrival_start_min=start_min,
                arrival_end_min=end_min,
            ),
            CrowdGroup(
                id="g-egress-central",
                name="Central Area Egress",
                total_size=s_size,
                entry_gate_id="stage",
                destination_node_id="gate-e",
                arrival_start_min=start_min,
                arrival_end_min=end_min,
            ),
        ]


    groups = []
    total_assigned = 0


    for i, dist in enumerate(entry_dist):
        gate_id = dist["gateId"]
        fraction = float(dist.get("fraction", 1.0 / len(entry_dist)))
        size = int(crowd_size * fraction)
        if i == len(entry_dist) - 1:
            size = crowd_size - total_assigned  # absorb rounding
        total_assigned += size

        # Arrival window based on pattern
        if arrival_pattern == "surge":
            start = -60.0
            end = 0.0
        elif arrival_pattern == "gradual":
            start = -90.0
            end = 30.0
        elif arrival_pattern == "peak-early":
            start = -60.0
            end = -10.0
        else:  # sustained
            start = -60.0
            end = duration * 0.5

        groups.append(CrowdGroup(
            id=f"g-auto-{gate_id}",
            name=f"Crowd via {gate_id}",
            total_size=size,
            entry_gate_id=gate_id,
            destination_node_id="stage",  # default destination
            arrival_start_min=start,
            arrival_end_min=end,
        ))

    return groups


def default_scenario_dict() -> dict:
    """Return the default Evening Concert scenario matching frontend DEFAULT_SCENARIO."""
    return {
        "id": "scenario-default",
        "name": "Evening Concert",
        "venueId": "venue-stadium-a",
        "crowdSize": 20000,
        "entryDistribution": [
            {"gateId": "gate-e", "fraction": 0.55},
            {"gateId": "gate-w", "fraction": 0.30},
            {"gateId": "gate-s", "fraction": 0.15},
        ],
        "crowdGroups": [
            {"id": "g-front", "name": "Front-of-stage crowd", "size": 9000,
             "entryGateId": "gate-e", "destinationNodeId": "stage",
             "arrivalStartMin": -60, "arrivalEndMin": 0},
            {"id": "g-mid", "name": "Mid-field crowd", "size": 7000,
             "entryGateId": "gate-e", "destinationNodeId": "stage",
             "arrivalStartMin": -45, "arrivalEndMin": 10},
            {"id": "g-west", "name": "West-side crowd", "size": 2500,
             "entryGateId": "gate-w", "destinationNodeId": "stage",
             "arrivalStartMin": -50, "arrivalEndMin": 5},
            {"id": "g-food", "name": "Food-court visitors", "size": 1500,
             "entryGateId": "gate-s", "destinationNodeId": "food-n",
             "arrivalStartMin": -40, "arrivalEndMin": 20},
        ],
        "timing": {
            "startMinutesOfDay": 1140,
            "durationMin": 180,
            "arrivalPattern": "surge",
            "departurePattern": "surge",
        },
        "entryRate": 600,
        "exitRate": 800,
        "specialConditions": [],
        "naturalLanguage": "A concert with 20,000 people starts at 7 PM. Most people enter through the east gate and food stalls are near the north corridor.",
    }
