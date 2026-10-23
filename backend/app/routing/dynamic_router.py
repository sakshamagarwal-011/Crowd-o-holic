from __future__ import annotations

"""
Dynamic routing — congestion-aware pathfinding and route management.
Routes are built from A* on the venue graph with dynamic edge costs.
"""

import time
from typing import Any

from app.graph.graph import VenueGraph
from app.graph.edges import GraphEdge
from app.core.config import settings
from app.simulation.state import RouteRecord, RouteChangeRecord


def _dynamic_cost(edge: GraphEdge, restricted_edges: dict[str, float] | None = None) -> float:
    """Congestion-aware edge cost used by router, with penalty for restricted corridors."""
    w_base = settings.routing_base_weight
    w_cong = settings.routing_congestion_weight
    w_cap = settings.routing_capacity_weight

    congestion_penalty = edge.density * w_cong
    cap_penalty = (edge.flow / max(edge.capacity, 1)) * w_cap
    restriction_penalty = 0.0
    if restricted_edges and edge.id in restricted_edges:
        factor = max(restricted_edges[edge.id], 0.05)
        restriction_penalty = (1.0 / factor) * 15.0

    return edge.base_cost * w_base + congestion_penalty + cap_penalty + restriction_penalty


def build_route(
    route_id: str,
    from_node: str,
    to_node: str,
    label: str,
    status: str,
    graph: VenueGraph,
    excluded_edges: set[str] | None = None,
    restricted_edges: dict[str, float] | None = None,
) -> RouteRecord | None:
    """Build a RouteRecord using A* pathfinding."""
    cost_fn = lambda e: _dynamic_cost(e, restricted_edges)
    edges = graph.find_path_edges(
        from_node, to_node,
        cost_fn=cost_fn,
        excluded_edges=excluded_edges,
    )
    if not edges:
        return None

    segments = [
        {
            "edgeId": e.id,
            "fromNodeId": e.from_node,
            "toNodeId": e.to_node,
        }
        for e in edges
    ]
    cost = sum(cost_fn(e) for e in edges)

    return RouteRecord(
        id=route_id,
        from_node_id=from_node,
        to_node_id=to_node,
        segments=segments,
        status=status,
        cost=cost,
        flow=0.0,
        label=label,
    )


def build_medical_responder_route(
    graph: VenueGraph,
    destination_node_id: str = "stage",
    source_node_id: str = "medical",
    excluded_edges: set[str] | None = None,
) -> RouteRecord | None:
    """Evaluate and verify feasible route for emergency medical responders."""
    return build_route(
        route_id="r-med-response",
        from_node=source_node_id,
        to_node=destination_node_id,
        label="Medical Responder Priority Access",
        status="active",
        graph=graph,
        excluded_edges=excluded_edges,
    )


def build_default_routes(graph: VenueGraph) -> list[RouteRecord]:
    """Build default routes matching the frontend's buildDefaultRoutes()."""
    routes = []
    defs = [
        ("r-ge-stage",    "gate-e", "stage",   "East Gate → Main Stage",   "active"),
        ("r-gw-stage",    "gate-w", "stage",   "West Gate → Main Stage",   "active"),
        ("r-gs-foodn",    "gate-s", "food-n",  "South Gate → North Food Court", "active"),
        ("r-stage-exitn", "stage",  "exit-n",  "Stage → North Exit",       "active"),
        ("r-stage-exitsw","stage",  "exit-sw", "Stage → SW Exit",          "active"),
        ("r-stage-exitse","stage",  "exit-se", "Stage → SE Exit",          "active"),
    ]
    for rid, frm, to, label, status in defs:
        r = build_route(rid, frm, to, label, status, graph)
        if r:
            routes.append(r)
    return routes


def recompute_routes(
    routes: list[RouteRecord],
    graph: VenueGraph,
    disabled_edges: set[str],
    sim_time_min: float,
    emergency_location: str | None = None,
    last_route_change_minute: float = -999.0,
    restricted_edges: dict[str, float] | None = None,
) -> tuple[list[RouteRecord], list[RouteChangeRecord]]:
    """
    Recompute routes when edge state changes.
    Handles disabled and restricted edges, marks affected routes as disabled, finds alternatives.
    Returns (updated_routes, new_route_changes).
    """
    changes: list[RouteChangeRecord] = []
    updated: list[RouteRecord] = []
    alt_ids: set[str] = set()

    restricted_edges = restricted_edges or {}
    heavy_restricted = {eid for eid, factor in restricted_edges.items() if factor <= 0.35}
    blocked_edges = set(disabled_edges) | heavy_restricted

    for r in routes:
        if r.id.startswith("r-alt-"):
            # Keep existing alts for now, will be rebuilt
            continue

        uses_blocked = any(seg["edgeId"] in blocked_edges for seg in r.segments)

        if uses_blocked and r.status != "disabled":
            # Mark as disabled, find alternative bypassing blocked/restricted corridors
            alt = build_route(
                f"r-alt-{r.from_node_id}-{r.to_node_id}-{int(sim_time_min)}",
                r.from_node_id, r.to_node_id,
                f"{r.label} (bypass)",
                "recommended",
                graph,
                excluded_edges=blocked_edges,
                restricted_edges=restricted_edges,
            )

            # If no direct bypass to destination, build relief evacuation route to closest exit
            if not alt:
                for relief_node, relief_name in (("exit-se", "SE Exit Bypass"), ("exit-n", "North Exit Bypass"), ("exit-sw", "SW Exit Bypass")):
                    if relief_node != r.from_node_id:
                        alt = build_route(
                            f"r-alt-{r.from_node_id}-{relief_node}-{int(sim_time_min)}",
                            r.from_node_id, relief_node,
                            f"{r.label} → {relief_name}",
                            "recommended",
                            graph,
                            excluded_edges=blocked_edges,
                            restricted_edges=restricted_edges,
                        )
                        if alt:
                            break

            affected_edge = next(
                (seg["edgeId"] for seg in r.segments if seg["edgeId"] in blocked_edges),
                "",
            )

            reason = (
                f"Route disabled due to emergency at {emergency_location}"
                if emergency_location
                else f"Route diverted: corridor {affected_edge} restricted/closed"
            )

            if alt:
                alt_ids.add(alt.id)
                updated.append(alt)
                changes.append(RouteChangeRecord(
                    id=f"rc-{int(sim_time_min)}-{r.id}",
                    at_minute=sim_time_min,
                    reason=reason,
                    from_route_id=r.id,
                    to_route_id=alt.id,
                    affected_edge_id=affected_edge,
                    redistributed_flow=r.flow,
                ))

            updated.append(RouteRecord(
                **{**r.__dict__, "status": "disabled", "flow": 0.0}
            ))

        elif r.status == "disabled" and not uses_blocked:
            # Re-enable
            updated.append(RouteRecord(**{**r.__dict__, "status": "active"}))
        else:
            updated.append(r)

    return updated, changes


def update_route_flows(routes: list[RouteRecord], graph: VenueGraph) -> None:
    """Update flow values on routes from current edge flows."""
    for r in routes:
        total_flow = sum(
            graph.get_edge(seg["edgeId"]).flow
            for seg in r.segments
            if graph.get_edge(seg["edgeId"]) is not None
        )
        r.flow = total_flow
