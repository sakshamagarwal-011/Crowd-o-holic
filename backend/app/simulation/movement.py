from __future__ import annotations

"""
Agent movement simulation.
Moves SimAgents along edges, handles arrival, congestion slow-down,
and agent replanning when edges become unavailable.
"""

import math
import random
from typing import TYPE_CHECKING

from app.simulation.crowd import SimAgent, CrowdGroup
from app.graph.graph import VenueGraph
from app.graph.nodes import GraphNode

if TYPE_CHECKING:
    pass

MAX_AGENTS_RENDERED = 1400   # visual cap — matches frontend constant


def spawn_agents(
    groups: list[CrowdGroup],
    sim_time_min: float,
    dt_sec: float,
    speed_mult: float,
    graph: VenueGraph,
    agents: list[SimAgent],
    next_agent_id: list[int],
    rng: random.Random,
    path_cache: dict[tuple[str, str], list[str] | None],
    restricted_edges: dict[str, float] | None = None,
    disabled_edges: set[str] | None = None,
) -> int:
    """Spawn new agents for groups that are currently in their arrival window."""
    spawned_count = 0
    disabled_edges = disabled_edges or set()
    restricted_edges = restricted_edges or {}

    for grp in groups:
        if grp.remaining_to_spawn <= 0:
            continue
        if sim_time_min < grp.arrival_start_min or sim_time_min > grp.arrival_end_min:
            continue

        # Check if the entry gate's outgoing edge or the gate itself is restricted or closed
        throttle_mult = 1.0
        gate_node = grp.entry_gate_id
        for neighbor, eid in graph.neighbors(gate_node):
            if eid in disabled_edges:
                throttle_mult = 0.0
                break
            if eid in restricted_edges:
                throttle_mult = min(throttle_mult, max(0.05, restricted_edges[eid]))

        if throttle_mult <= 0.0:
            continue

        rate = grp.spawn_rate_per_min() * throttle_mult
        to_spawn_float = rate * (dt_sec / 60.0) * speed_mult
        n = min(
            int(to_spawn_float) + (1 if rng.random() < (to_spawn_float % 1) else 0),
            grp.remaining_to_spawn,
            MAX_AGENTS_RENDERED - len(agents),
        )

        for _ in range(n):
            if len(agents) >= MAX_AGENTS_RENDERED:
                break
            agent = _spawn_one(
                grp, graph, next_agent_id, rng, path_cache,
                restricted_edges=restricted_edges,
                disabled_edges=disabled_edges,
            )
            if agent:
                agents.append(agent)
                grp.spawned += 1
                grp.active += 1
                spawned_count += 1

    return spawned_count


def _spawn_one(
    grp: CrowdGroup,
    graph: VenueGraph,
    next_agent_id: list[int],
    rng: random.Random,
    path_cache: dict[tuple[str, str], list[str] | None],
    restricted_edges: dict[str, float] | None = None,
    disabled_edges: set[str] | None = None,
) -> SimAgent | None:
    start_node = graph.get_node(grp.entry_gate_id)
    if start_node is None:
        return None

    dest = grp.destination_node_id
    from app.routing.dynamic_router import _dynamic_cost
    cost_fn = lambda e: _dynamic_cost(e, restricted_edges)

    path = graph.find_path(
        grp.entry_gate_id,
        dest,
        cost_fn=cost_fn,
        excluded_edges=disabled_edges,
    )

    if not path or len(path) < 2:
        return None

    first_edge = graph.get_edge_between(path[0], path[1])
    if first_edge is None or not first_edge.is_traversable or (disabled_edges and first_edge.id in disabled_edges):
        # Try to find alternative first step
        for neighbor, eid in graph.neighbors(path[0]):
            e = graph.get_edge(eid)
            if e and e.is_traversable and (not disabled_edges or eid not in disabled_edges):
                first_edge = e
                path = [path[0], neighbor] + path[2:]
                break
        else:
            return None

    aid = next_agent_id[0]
    next_agent_id[0] += 1

    return SimAgent(
        id=aid,
        x=start_node.x + (rng.random() - 0.5) * 20,
        y=start_node.y + (rng.random() - 0.5) * 20,
        vx=0.0, vy=0.0,
        group_id=grp.id,
        from_node_id=path[0],
        to_node_id=path[1],
        edge_id=first_edge.id,
        progress=0.0,
        speed=22.0 + rng.random() * 12.0,
        destination_node_id=dest,
    )


def move_agents(
    agents: list[SimAgent],
    dt_sec: float,
    speed_mult: float,
    graph: VenueGraph,
    groups: list[CrowdGroup],
    rng: random.Random,
    path_cache: dict[tuple[str, str], list[str] | None],
    restricted_edges: dict[str, float] | None = None,
    disabled_edges: set[str] | None = None,
) -> tuple[list[SimAgent], int]:
    """
    Move all agents one timestep. Returns (remaining_agents, exited_count).
    """
    remaining: list[SimAgent] = []
    exited_count = 0
    group_map = {g.id: g for g in groups}
    disabled_edges = disabled_edges or set()

    for a in agents:
        edge = graph.get_edge(a.edge_id)

        # Edge closed under agent or in disabled_edges — replan immediately
        if edge is None or not edge.is_traversable or a.edge_id in disabled_edges:
            success = _replan_agent(
                a, graph, group_map, rng, path_cache,
                restricted_edges=restricted_edges, disabled_edges=disabled_edges,
            )
            if success:
                remaining.append(a)
            else:
                exited_count += 1  # stuck or evacuated
            continue

        from_node = graph.get_node(a.from_node_id)
        to_node = graph.get_node(a.to_node_id)
        if from_node is None or to_node is None:
            continue

        dx = to_node.x - from_node.x
        dy = to_node.y - from_node.y
        length = math.hypot(dx, dy)

        if length < 0.1:
            _advance_agent(
                a, graph, group_map, remaining, rng, path_cache,
                restricted_edges=restricted_edges, disabled_edges=disabled_edges,
            )
            if a.edge_id:
                remaining.append(a) if a not in remaining else None
            continue

        congestion_factor = max(0.3, 1.0 - edge.density * 0.6)
        if restricted_edges and edge.id in restricted_edges:
            # Metering/restrictions regulate inflow at the entrance,
            # but agents currently inside the corridor proceed at clearing speed to drain the chokepoint
            congestion_factor = max(congestion_factor, 1.15)

        step = (a.speed * congestion_factor * dt_sec * speed_mult) / length
        a.progress += step

        target_dest = a.destination_node_id or (group_map[a.group_id].destination_node_id if a.group_id in group_map else "")

        if a.progress >= 1.0:
            arrived = a.to_node_id
            if arrived == target_dest:
                # Destination reached
                grp = group_map.get(a.group_id)
                if grp:
                    grp.active = max(0, grp.active - 1)
                    grp.exited += 1
                exited_count += 1
            else:
                success = _replan_agent(
                    a, graph, group_map, rng, path_cache,
                    from_node=arrived, restricted_edges=restricted_edges, disabled_edges=disabled_edges,
                )
                if success:
                    remaining.append(a)
                else:
                    exited_count += 1
        else:
            a.x = from_node.x + dx * a.progress
            a.y = from_node.y + dy * a.progress
            a.vx = dx / length
            a.vy = dy / length
            remaining.append(a)

    return remaining, exited_count


def _advance_agent(
    a: SimAgent,
    graph: VenueGraph,
    group_map: dict[str, CrowdGroup],
    remaining: list[SimAgent],
    rng: random.Random,
    path_cache: dict[tuple[str, str], list[str] | None],
    restricted_edges: dict[str, float] | None = None,
    disabled_edges: set[str] | None = None,
) -> None:
    arrived = a.to_node_id
    target_dest = a.destination_node_id or (group_map[a.group_id].destination_node_id if a.group_id in group_map else "")
    if arrived == target_dest:
        grp = group_map.get(a.group_id)
        if grp:
            grp.active = max(0, grp.active - 1)
            grp.exited += 1
        a.edge_id = ""
    else:
        _replan_agent(
            a, graph, group_map, rng, path_cache,
            from_node=arrived, restricted_edges=restricted_edges, disabled_edges=disabled_edges,
        )


def _replan_agent(
    a: SimAgent,
    graph: VenueGraph,
    group_map: dict[str, CrowdGroup],
    rng: random.Random,
    path_cache: dict[tuple[str, str], list[str] | None],
    from_node: str | None = None,
    restricted_edges: dict[str, float] | None = None,
    disabled_edges: set[str] | None = None,
) -> bool:
    """Replan agent path. Returns True if successful."""
    here = from_node or a.to_node_id
    grp = group_map.get(a.group_id)
    if grp is None:
        return False

    dest = a.destination_node_id if a.destination_node_id else grp.destination_node_id
    if here == dest:
        grp.active = max(0, grp.active - 1)
        grp.exited += 1
        a.edge_id = ""
        return False

    from app.routing.dynamic_router import _dynamic_cost
    cost_fn = lambda e: _dynamic_cost(e, restricted_edges)
    path = graph.find_path(here, dest, cost_fn=cost_fn, excluded_edges=disabled_edges)

    if not path or len(path) < 2:
        # If destination is inaccessible due to corridor closure, route to nearest open exit
        for relief in ("exit-se", "exit-n", "exit-sw"):
            if relief != here:
                alt = graph.find_path(here, relief, cost_fn=cost_fn, excluded_edges=disabled_edges)
                if alt and len(alt) >= 2:
                    path = alt
                    a.destination_node_id = relief
                    break
        else:
            return False

    e = graph.get_edge_between(path[0], path[1])
    if e is None or not e.is_traversable or (disabled_edges and e.id in disabled_edges):
        return False

    from_n = graph.get_node(path[0])
    a.from_node_id = path[0]
    a.to_node_id = path[1]
    a.edge_id = e.id
    a.progress = 0.0
    if from_n:
        a.x = from_n.x
        a.y = from_n.y
    return True


def update_edge_metrics(
    agents: list[SimAgent],
    graph: VenueGraph,
    edge_density_offsets: dict[str, float] | None = None,
) -> None:
    """Update flow/density on all edges based on current agent distribution and validated observations."""
    counts: dict[str, int] = {}
    for a in agents:
        if a.edge_id:
            counts[a.edge_id] = counts.get(a.edge_id, 0) + 1

    offsets = edge_density_offsets or {}

    # Reset all edges
    for e in graph.edges.values():
        e.flow = 0.0
        offset = offsets.get(e.id, 0.0)
        e.density = min(1.0, offset)

    # Update from counts
    for edge_id, count in counts.items():
        e = graph.get_edge(edge_id)
        if e is None:
            continue
        cap = max(e.capacity * 0.85, 30.0)
        offset = offsets.get(e.id, 0.0)
        e.density = min(1.0, (count / cap) + offset)
        e.flow = round(min(count * 2.0, e.capacity * 1.5), 1)

    # Set edge statuses based on density
    for e in graph.edges.values():
        if e.status in ("emergency-closed", "closed"):
            continue
        if e.density > 0.8:
            e.status = "congested"
        elif e.status == "congested" and e.density <= 0.7:
            e.status = "open"
