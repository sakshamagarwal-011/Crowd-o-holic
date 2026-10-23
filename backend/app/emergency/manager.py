from __future__ import annotations

"""
Emergency event manager.
Handles emergency events: closes edges/nodes, recalculates routes,
triggers AI safety analysis. Simulation continues through emergencies.
"""

import time
from typing import TYPE_CHECKING

from app.graph.graph import VenueGraph
from app.simulation.state import EmergencyRecord, SimulationRuntimeState
from app.routing.dynamic_router import recompute_routes, build_default_routes
from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

log = get_logger(__name__)

_EMERGENCY_TYPE_LABELS = {
    "fire": "Fire",
    "medical": "Medical incident",
    "structural": "Structural failure",
    "security": "Security threat",
    "crowd-crush": "Crowd crush risk",
    "gate-failure": "Gate failure",
}


def trigger_emergency(
    sim_state: SimulationRuntimeState,
    graph: VenueGraph,
    emergency_type: str,
    node_id: str,
) -> EmergencyRecord:
    """
    Trigger an emergency at node_id.
    Closes all edges connected to the node, recalculates routes.
    """
    if sim_state.emergency and sim_state.emergency.active:
        raise ValueError("An emergency is already active")

    node = graph.get_node(node_id)
    if node is None:
        raise ValueError(f"Node '{node_id}' not found")

    type_label = _EMERGENCY_TYPE_LABELS.get(emergency_type, emergency_type)

    # Close edges around the node
    closed_ids = graph.close_node_edges(node_id)
    for eid in closed_ids:
        sim_state.disabled_edges.add(eid)

    # Invalidate path cache — must recompute with new disabled edges
    sim_state.path_cache.clear()

    em = EmergencyRecord(
        id=f"em-{int(time.time())}",
        type=emergency_type,
        location=node.label,
        node_id=node_id,
        at_minute=sim_state.sim_time_min,
        active=True,
        closed_edge_ids=closed_ids,
        summary=(
            f"{type_label} reported at {node.label}. "
            f"{len(closed_ids)} route segment(s) disabled and rerouting initiated."
        ),
    )
    sim_state.emergency = em

    # Recompute routes
    updated_routes, changes = recompute_routes(
        sim_state.routes,
        graph,
        sim_state.disabled_edges,
        sim_state.sim_time_min,
        emergency_location=node.label,
    )
    sim_state.routes = updated_routes
    sim_state.route_changes = changes + sim_state.route_changes

    sim_state.push_timeline(
        "emergency",
        f"EMERGENCY: {type_label} at {node.label}",
        f"{len(closed_ids)} route segment(s) disabled. Rerouting in progress.",
        severity="emergency",
    )

    log.warning(
        "Emergency triggered | type=%s node=%s closed_edges=%s",
        emergency_type, node_id, closed_ids,
    )
    return em


def clear_emergency(
    sim_state: SimulationRuntimeState,
    graph: VenueGraph,
) -> None:
    """
    Clear the active emergency.
    Reopens previously closed edges, recalculates routes.
    """
    em = sim_state.emergency
    if em is None:
        return

    em.active = False

    # Reopen edges
    for eid in em.closed_edge_ids:
        graph.open_edge(eid)
        sim_state.disabled_edges.discard(eid)

    # Invalidate path cache
    sim_state.path_cache.clear()

    # Recompute routes
    updated_routes, changes = recompute_routes(
        sim_state.routes,
        graph,
        sim_state.disabled_edges,
        sim_state.sim_time_min,
    )
    sim_state.routes = updated_routes
    sim_state.route_changes = changes + sim_state.route_changes

    sim_state.push_timeline(
        "emergency",
        "Emergency cleared",
        f"{em.location} reopened. Routes restored.",
    )

    sim_state.emergency = None
    log.info("Emergency cleared | location=%s", em.location)


def apply_scenario_incidents(
    sim_state: SimulationRuntimeState,
    graph: VenueGraph,
    incidents: list[Any],
) -> None:
    """
    Apply validated scenario incidents and observations onto simulation state and venue graph.
    Distinguishes high density, congestion, restricted movement, and emergency blockages.
    """
    from app.routing.dynamic_router import build_medical_responder_route

    sim_state.incidents = []
    sim_state.restricted_edges.clear()
    sim_state.edge_density_offsets.clear()

    for item in incidents:
        inc = item if isinstance(item, dict) else item.model_dump()
        sim_state.incidents.append(inc)

        inc_type = inc.get("type", "other")
        node_id = inc.get("resolved_node_id")
        edge_id = inc.get("resolved_edge_id")
        severity = inc.get("severity", "moderate")
        location = inc.get("reported_location", "venue")

        # 1. Medical emergency
        if inc_type == "medical":
            if node_id and node_id in graph.nodes:
                target_node_obj = graph.get_node(node_id)
                target_label = target_node_obj.label if target_node_obj else node_id
                em = EmergencyRecord(
                    id=inc.get("id", f"em-{int(time.time())}"),
                    type="medical",
                    location=target_label,
                    node_id=node_id,
                    at_minute=sim_state.sim_time_min,
                    active=True,
                    closed_edge_ids=[],
                    summary=f"Medical emergency reported at {target_label}. Immediate medical assistance requested.",
                )
                sim_state.emergency = em

                # Evaluate feasible medical responder access route from medical station
                med_route = build_medical_responder_route(graph, destination_node_id=node_id)
                if med_route:
                    sim_state.routes = [r for r in sim_state.routes if r.id != med_route.id] + [med_route]
                    sim_state.medical_routes = [med_route]
                    sim_state.push_timeline(
                        "emergency",
                        f"EMERGENCY: Medical assistance requested at {target_label}",
                        "Priority medical responder route evaluated from Medical Station.",
                        severity="emergency",
                    )
                else:
                    sim_state.push_timeline(
                        "emergency",
                        f"EMERGENCY: Medical assistance requested at {target_label}",
                        "WARNING: No feasible direct route available from Medical Station to incident site.",
                        severity="emergency",
                    )
            else:
                # Unresolved medical incident location — preserve without inventing fake node
                em = EmergencyRecord(
                    id=inc.get("id", f"em-{int(time.time())}"),
                    type="medical",
                    location=location,
                    node_id="",
                    at_minute=sim_state.sim_time_min,
                    active=True,
                    closed_edge_ids=[],
                    summary=f"Medical emergency reported at unverified location '{location}'. Operator dispatch required.",
                )
                sim_state.emergency = em
                sim_state.push_timeline(
                    "emergency",
                    f"EMERGENCY: Medical assistance requested at {location}",
                    "Location unmapped in venue graph. Operator manual verification required.",
                    severity="emergency",
                )

        # 2. Restricted corridor (movement restriction, NOT complete blockage)
        elif inc_type == "restricted-corridor":
            if edge_id and edge_id in graph.edges:
                sim_state.restricted_edges[edge_id] = 0.4  # 60% speed slowdown
                edge = graph.get_edge(edge_id)
                if edge and edge.status == "open":
                    edge.status = "congested"
                sim_state.push_timeline(
                    "route-change",
                    f"Corridor restricted: {location}",
                    f"Corridor {edge_id} restricted; pedestrian routing penalty and slowdown applied.",
                    severity="moderate",
                )
            else:
                sim_state.push_timeline(
                    "alert",
                    f"Corridor restriction reported: {location}",
                    "Reported corridor not mapped to a verified edge. Preserving incident for operator review.",
                    severity="moderate",
                )

        # 3. Congestion observation
        elif inc_type == "congestion":
            affected_edges: list[str] = []
            if edge_id and edge_id in graph.edges:
                affected_edges.append(edge_id)
            elif node_id and node_id in graph.nodes:
                for _, eid in graph.neighbors(node_id):
                    affected_edges.append(eid)

            for eid in affected_edges:
                sim_state.edge_density_offsets[eid] = 0.35
                edge = graph.get_edge(eid)
                if edge and edge.status == "open":
                    edge.status = "congested"

            sim_state.push_timeline(
                "bottleneck",
                f"Congestion observation: {location}",
                f"Inflow density elevated across {len(affected_edges)} corridor(s); monitoring queues.",
                severity="moderate",
            )

        # 4. High / increasing crowd density observation
        elif inc_type == "observation" or "density" in inc.get("description", "").lower():
            affected_edges = []
            if edge_id and edge_id in graph.edges:
                affected_edges.append(edge_id)
            elif node_id and node_id in graph.nodes:
                for _, eid in graph.neighbors(node_id):
                    affected_edges.append(eid)

            for eid in affected_edges:
                sim_state.edge_density_offsets[eid] = 0.30

            sim_state.push_timeline(
                "alert",
                f"Density surge observed: {location}",
                f"Telemetry indicates elevated crowd density on {len(affected_edges)} corridor segment(s).",
                severity="high",
            )
