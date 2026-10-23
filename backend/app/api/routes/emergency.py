from __future__ import annotations

import json
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.services import simulation_service
from app.emergency.manager import trigger_emergency, clear_emergency

log = get_logger(__name__)

router = APIRouter(prefix="/api/simulations", tags=["Emergency"])


class TriggerEmergencyRequest(BaseModel):
    type: str       # fire|medical|structural|security|crowd-crush|gate-failure
    node_id: str


@router.post("/{simulation_id}/emergency")
async def trigger_em(simulation_id: str, req: TriggerEmergencyRequest):
    engine = simulation_service.get_simulation(simulation_id)
    em = trigger_emergency(engine.state, engine.graph, req.type, req.node_id)
    return em.to_frontend_dict()


@router.delete("/{simulation_id}/emergency")
async def clear_em(simulation_id: str):
    engine = simulation_service.get_simulation(simulation_id)
    clear_emergency(engine.state, engine.graph)
    return {"status": "cleared"}


class InterveneRequest(BaseModel):
    action: str = "divert"  # divert | restrict | open_bypass | reopen | clear
    edge_id: str | None = None
    node_id: str | None = None
    target_node_id: str | None = None
    reason: str | None = None


@router.post("/{simulation_id}/intervene")
async def apply_intervention(simulation_id: str, req: InterveneRequest):
    engine = simulation_service.get_simulation(simulation_id)
    sim_state = engine.state
    graph = engine.graph

    # Normalize edge_id if provided
    edge_id = req.edge_id.strip() if req.edge_id else None
    if edge_id:
        if edge_id not in graph.edges:
            if edge_id.startswith("c-") and ("e-" + edge_id[2:]) in graph.edges:
                edge_id = "e-" + edge_id[2:]
            elif edge_id.startswith("e-") and ("c-" + edge_id[2:]) in graph.edges:
                edge_id = "c-" + edge_id[2:]
            else:
                from app.graph.resolver import resolve_location
                res = resolve_location(edge_id, graph)
                if res.is_resolved and res.resolved_edge_id:
                    edge_id = res.resolved_edge_id

    # Determine relief destination node
    target_target = req.target_node_id
    if not target_target:
        if edge_id and ("e" in edge_id or "east" in (req.reason or "").lower()):
            target_target = "exit-se"
        elif edge_id and ("w" in edge_id or "west" in (req.reason or "").lower()):
            target_target = "exit-sw"
        else:
            target_target = "exit-n"

    target_obj = graph.get_node(target_target)
    target_label = target_obj.label if target_obj else target_target

    if req.action in ("close", "block", "close_corridor"):
        if edge_id and edge_id in graph.edges:
            sim_state.disabled_edges.add(edge_id)
            if edge_id in sim_state.restricted_edges:
                del sim_state.restricted_edges[edge_id]
            edge = graph.get_edge(edge_id)
            if edge:
                edge.disabled = True
                edge.status = "closed"
        elif req.node_id and req.node_id in graph.nodes:
            closed_ids = graph.close_node_edges(req.node_id)
            for eid in closed_ids:
                sim_state.disabled_edges.add(eid)

        sim_state.push_timeline(
            "route-change",
            f"OPERATOR INTERVENTION: Corridor {edge_id or req.node_id} CLOSED",
            f"Corridor closed. Traffic dynamically diverted to {target_label}.",
            severity="high",
        )

    elif req.action in ("divert", "restrict", "meter"):
        if edge_id and edge_id in graph.edges:
            sim_state.restricted_edges[edge_id] = 0.25  # heavy flow penalty (75% reduction)
            if edge_id in sim_state.edge_density_offsets:
                del sim_state.edge_density_offsets[edge_id]
        elif req.node_id and req.node_id in graph.nodes:
            closed_ids = graph.close_node_edges(req.node_id)
            for eid in closed_ids:
                sim_state.disabled_edges.add(eid)

        sim_state.push_timeline(
            "route-change",
            f"OPERATOR INTERVENTION: Corridor {edge_id or req.node_id} RESTRICTED",
            f"Flow metered & restricted. Active crowds migrating towards {target_label}.",
            severity="moderate",
        )

    elif req.action == "open_bypass":
        # Clear restrictions on bypass routes and re-route surplus agents
        if edge_id and edge_id in sim_state.restricted_edges:
            del sim_state.restricted_edges[edge_id]
        if edge_id and edge_id in sim_state.disabled_edges:
            sim_state.disabled_edges.remove(edge_id)
        if edge_id and edge_id in sim_state.edge_density_offsets:
            del sim_state.edge_density_offsets[edge_id]
        if edge_id:
            edge = graph.get_edge(edge_id)
            if edge:
                edge.status = "open"
                edge.disabled = False

        sim_state.push_timeline(
            "route-change",
            f"OPERATOR INTERVENTION: Opened Relief Route {target_label}",
            f"Active crowd redirected to {target_label} to absorb excess concourse rush.",
            severity="low",
        )

    elif req.action in ("reopen", "clear"):
        if edge_id:
            # Reopen single corridor
            if edge_id in sim_state.restricted_edges:
                del sim_state.restricted_edges[edge_id]
            if edge_id in sim_state.disabled_edges:
                sim_state.disabled_edges.remove(edge_id)
            edge = graph.get_edge(edge_id)
            if edge:
                edge.status = "open"
                edge.disabled = False
            sim_state.push_timeline(
                "route-change",
                f"OPERATOR INTERVENTION: Corridor {edge_id} Reopened",
                "Flow restrictions lifted for corridor.",
                severity="low",
            )
        else:
            # Reopen all corridors
            sim_state.restricted_edges.clear()
            sim_state.disabled_edges.clear()
            graph.reset_edge_flows()
            for edge in graph.edges.values():
                edge.status = "open"
                edge.disabled = False
            for a in sim_state.agents:
                a.destination_node_id = "stage"
            for grp in sim_state.groups:
                grp.destination_node_id = "stage"
            from app.routing.dynamic_router import build_default_routes
            sim_state.routes = build_default_routes(graph)
            sim_state.push_timeline(
                "route-change",
                "OPERATOR INTERVENTION: All Corridors Reopened",
                "Flow restrictions lifted. Standard bidirectional routing restored across all sectors.",
                severity="low",
            )

    # ── Actively migrate routes and crowds ───────────────────────────────────
    sim_state.path_cache.clear()

    if req.action in ("close", "block", "close_corridor", "divert", "restrict", "meter", "open_bypass"):
        # 1. Update crowd group destination or gate diversion if applicable
        if req.action in ("divert", "open_bypass"):
            if target_target == "gate-s":
                for grp in sim_state.groups:
                    if grp.entry_gate_id == "gate-e":
                        grp.entry_gate_id = "gate-s"
            elif target_target in ("exit-se", "exit-n", "exit-sw"):
                for grp in sim_state.groups:
                    if grp.entry_gate_id == "gate-e" and "mid" in grp.id:
                        grp.destination_node_id = target_target

        # 2. Recompute routes considering both disabled and heavily restricted edges
        from app.routing.dynamic_router import recompute_routes
        updated_routes, changes = recompute_routes(
            sim_state.routes,
            graph,
            sim_state.disabled_edges,
            sim_state.sim_time_min,
            emergency_location=target_label,
            restricted_edges=sim_state.restricted_edges,
        )
        sim_state.routes = updated_routes
        sim_state.route_changes = changes + sim_state.route_changes

        # 3. Actively migrate and reroute existing agents
        from app.simulation.movement import _replan_agent, update_edge_metrics
        group_map = {g.id: g for g in sim_state.groups}
        # Clear any artificial incident density offsets on diverted edge
        if edge_id and edge_id in sim_state.edge_density_offsets:
            del sim_state.edge_density_offsets[edge_id]

        for a in sim_state.agents:
            should_reroute = False

            # Directly on affected edge
            if edge_id and a.edge_id == edge_id:
                should_reroute = True
            # Approaching junction or node connected to affected edge
            elif edge_obj and (a.to_node_id in (edge_obj.from_node, edge_obj.to_node) or a.from_node_id in (edge_obj.from_node, edge_obj.to_node)):
                should_reroute = True
            # Sector-based diversion
            elif req.action in ("divert", "open_bypass"):
                if target_target == "exit-se" and (a.from_node_id in ("j-e", "gate-e", "j-se", "j-ne") or a.to_node_id in ("j-e", "j-se", "stage")):
                    should_reroute = True
                elif target_target == "exit-n" and (a.from_node_id in ("j-n", "food-n", "j-nw", "j-ne") or a.to_node_id in ("j-n", "food-n", "stage")):
                    should_reroute = True
                elif target_target == "exit-sw" and (a.from_node_id in ("j-w", "gate-w", "j-sw") or a.to_node_id in ("j-w", "j-sw", "stage")):
                    should_reroute = True
                elif target_target in ("gate-s", "food-s") and (a.from_node_id in ("j-e", "gate-e", "j-se") or a.to_node_id in ("j-e", "j-se")):
                    should_reroute = True
                elif req.action == "divert" and (a.id % 3 != 0):
                    should_reroute = True

            if should_reroute:
                a.destination_node_id = target_target
                _replan_agent(
                    a,
                    graph,
                    group_map,
                    engine._rng,
                    sim_state.path_cache,
                    from_node=a.to_node_id or a.from_node_id,
                    restricted_edges=sim_state.restricted_edges,
                    disabled_edges=sim_state.disabled_edges,
                )

        update_edge_metrics(sim_state.agents, graph, sim_state.edge_density_offsets)

    metrics, safety = engine.get_snapshot_data()
    from app.realtime.broadcaster import broadcast_snapshot
    await broadcast_snapshot(simulation_id, sim_state, graph, metrics, safety)

    return {
        "status": "success",
        "action": req.action,
        "diverted_to": target_label,
        "restricted_edges": list(sim_state.restricted_edges.keys()),
        "disabled_edges": list(sim_state.disabled_edges),
    }


class MitigateRequest(BaseModel):
    corridor_focus: str | None = None  # e.g. "east", "west", or specific edge_id


@router.post("/{simulation_id}/mitigate-ai")
async def generate_ai_mitigation(simulation_id: str, req: MitigateRequest | None = None):
    """
    Generate tactical solutions using local Ollama GPU model (qwen2.5:3b) or rule-engine tactician,
    specifically designed to stop crowd rush, corridor bottlenecks, and high volume surges (e.g. East Gate).
    """
    engine = simulation_service.get_simulation(simulation_id)
    sim_state = engine.state
    graph = engine.graph
    metrics, safety = engine.get_snapshot_data()

    bottlenecks = safety.get("bottlenecks", [])
    people = metrics.get("peopleCount", 0)
    risk_level = safety.get("riskLevel", "low")
    risk_score = safety.get("riskScore", 0)

    # Determine focus from request or active bottlenecks
    focus = (req.corridor_focus if req else None) or "auto"
    
    # Check if East Gate has major traffic or if East is specifically requested
    is_east_focus = focus in ("east", "gate-e", "e-ge-je")
    if not is_east_focus and bottlenecks:
        for b in bottlenecks:
            eid = b.get("edgeId", "")
            if any(k in eid for k in ["ge", "je", "jne", "jse"]):
                is_east_focus = True
                break

    # Compile active bottleneck descriptions
    bn_lines = []
    if is_east_focus:
        primary_congested_edge = "e-ge-je"
        primary_location = "East Gate / Main Entrance Corridor"
    else:
        primary_congested_edge = "e-gw-jw"
        primary_location = "West Corridor"

    for bn in bottlenecks:
        loc = bn.get("location", "Corridor")
        eid = bn.get("edgeId", primary_congested_edge)
        util = bn.get("capacityUtilization", 0.8)
        bn_lines.append(f"- Location: {loc} (Edge ID: {eid}), Capacity Utilization: {util:.0%}, Risk: {bn.get('risk')}")
        if eid and not (is_east_focus and "gw" in eid):
            primary_congested_edge = eid
            primary_location = loc

    if not bn_lines:
        if is_east_focus:
            bn_lines.append("- Heavy pedestrian rush entering via East Gate (e-ge-je) exceeding concourse capacity.")
        else:
            bn_lines.append("- Moderate build-up observed approaching main concourses (Edge: e-gw-jw).")

    system_prompt = (
        "You are an expert crowd flow and venue safety tactician. "
        "Your task is to analyze crowd rush and recommend specific, actionable operational interventions. "
        "You must output ONLY valid JSON."
    )

    user_prompt = f"""VENUE: Stadium A
ACTIVE CROWD: {people:,} attendees
RISK SCORE: {risk_score}/100 ({risk_level.upper()})
CONGESTED CORRIDORS / BOTTLENECKS:
{chr(10).join(bn_lines)}

AVAILABLE RELIEF EXITS IN GRAPH:
- exit-se: South-East Exit (Capacity: 900/hr, closest evacuation exit for East Gate & East Junction)
- exit-n: North Exit (Capacity: 2,000/hr, high-capacity Emergency Evacuation Route)
- exit-sw: South-West Exit (Capacity: 900/hr, closest evacuation exit for West Gate & West Junction)
- gate-s: South Gate / Plaza (Capacity: 800/hr, low congestion perimeter relief)

PRIMARY CONGESTED CORRIDOR: {primary_congested_edge} ({primary_location})
TARGET CROWD SOURCE: {"East Gate arrival surge (55-60% of attendees)" if is_east_focus else "Active corridor bottleneck"}

Formulate an immediate tactical mitigation plan to disperse the rush and clear the blocked corridor.
Return JSON with this exact schema:
{{
  "situation_assessment": "1 sentence describing the bottleneck and cause of rush",
  "tactical_strategy": "1-2 sentences outlining the operational diversion and corridor control strategy (in English/Hindi)",
  "actions": [
    {{
      "id": "act-1",
      "action_type": "restrict",
      "edge_id": "{primary_congested_edge}",
      "target_node_id": "{'exit-se' if is_east_focus else 'exit-n'}",
      "title": "Restrict / Meter Inflow on {primary_location}",
      "instruction": "Close or throttle corridor {primary_congested_edge} to halt further crowd compression into the junction.",
      "expected_outcome": "Reduces incoming surge by 50% and prevents dangerous queue accumulation."
    }},
    {{
      "id": "act-2",
      "action_type": "open_bypass",
      "edge_id": "{primary_congested_edge}",
      "target_node_id": "{'exit-se' if is_east_focus else 'exit-n'}",
      "title": "Open {'South-East Exit Bypass (exit-se)' if is_east_focus else 'North Exit Bypass (exit-n)'}",
      "instruction": "Open auxiliary relief gates and redirect pedestrian flow away from bottleneck.",
      "expected_outcome": "Disperses up to {'900' if is_east_focus else '2,000'} attendees/hour away from the primary bottleneck."
    }},
    {{
      "id": "act-3",
      "action_type": "divert",
      "edge_id": "{primary_congested_edge}",
      "target_node_id": "gate-s",
      "title": "Divert Flow to South Gate / Plaza (gate-s)",
      "instruction": "Deploy stewards to redirect peripheral concourse crowd toward South Gate.",
      "expected_outcome": "Balances venue distribution across less congested southern perimeter."
    }}
  ]
}}
"""

    model_used = settings.ollama_model
    try:
        async with httpx.AsyncClient(timeout=14.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            parsed = json.loads(content)
            actions = parsed.get("actions", [])
            for act in actions:
                eid = act.get("edge_id")
                if eid and eid not in graph.edges:
                    if eid.startswith("c-") and ("e-" + eid[2:]) in graph.edges:
                        act["edge_id"] = "e-" + eid[2:]
                    elif eid.startswith("e-") and ("c-" + eid[2:]) in graph.edges:
                        act["edge_id"] = "c-" + eid[2:]

            return {
                "status": "success",
                "model": f"{model_used} (Ollama GPU)",
                "situation_assessment": parsed.get("situation_assessment", f"Congestion detected at {primary_location}."),
                "tactical_strategy": parsed.get("tactical_strategy", f"Restrict {primary_location} inflow aur crowd ko relief bypass ki taraf divert karein."),
                "actions": actions,
                "restricted_edges": list(sim_state.restricted_edges.keys()),
            }
    except Exception as exc:
        log.warning("Ollama mitigation generation fallback (%s: %s)", type(exc).__name__, exc)
        # Robust context-aware fallback using deterministic venue topology
        if is_east_focus:
            return {
                "status": "success",
                "model": "Rule-Engine Tactician (Ollama Fallback)",
                "situation_assessment": "Bhaari bheed East Gate (e-ge-je) se enter ho rahi hai, jisse East Junction (j-e) block ho raha hai.",
                "tactical_strategy": "East Gate inflow ko meter/restrict karein, aur public ko South-East Exit (exit-se) tatha North Exit (exit-n) bypass ki taraf divert karein.",
                "actions": [
                    {
                        "id": "act-1",
                        "action_type": "restrict",
                        "edge_id": "e-ge-je",
                        "target_node_id": "exit-se",
                        "title": "Throttle / Meter East Gate Inflow (e-ge-je)",
                        "instruction": "East Gate turnstiles ko 50% restrict karein taaki East Junction par crowd crush ka risk na bane.",
                        "expected_outcome": "East corridor arrival flow 50% reduce hoga aur concourse queue control mein rahegi.",
                    },
                    {
                        "id": "act-2",
                        "action_type": "open_bypass",
                        "edge_id": "e-ge-je",
                        "target_node_id": "exit-se",
                        "title": "Open South-East Exit Relief Bypass (exit-se)",
                        "instruction": "SE Corridor (j-se) ke zariye South-East Exit (exit-se) khol kar 900 people/hour ko direct evacuate karein.",
                        "expected_outcome": "East concourse se direct 900 log per hour evacuate ho kar bahar nikal jayenge.",
                    },
                    {
                        "id": "act-3",
                        "action_type": "divert",
                        "edge_id": "e-ge-je",
                        "target_node_id": "exit-n",
                        "title": "Divert Stage-bound East Flow to North Exit (exit-n)",
                        "instruction": "NE Corridor (j-ne -> j-n) ke through crowd ko North Exit (exit-n) bypass par reroute karein.",
                        "expected_outcome": "2,000/hr capacity North bypass open ho kar East-Stage corridor congestion khatam karega.",
                    },
                    {
                        "id": "act-4",
                        "action_type": "divert",
                        "edge_id": "e-ge-je",
                        "target_node_id": "gate-s",
                        "title": "Divert Peripheral Flow to South Gate Plaza (gate-s)",
                        "instruction": "Security stewards deploy karke peripheral public ko South Gate (gate-s) ki taraf guide karein.",
                        "expected_outcome": "Southern boundary par crowd distribute ho kar primary bottleneck ko relief degi.",
                    },
                ],
                "restricted_edges": list(sim_state.restricted_edges.keys()),
            }
        else:
            return {
                "status": "success",
                "model": "Rule-Engine Tactician (Ollama Fallback)",
                "situation_assessment": f"Heavy pedestrian accumulation detected along {primary_location} ({primary_congested_edge}) exceeding safe density limits.",
                "tactical_strategy": f"Isolate {primary_location} inflow, close/restrict corridor {primary_congested_edge}, aur crowd ko turant North Exit bypass (exit-n) aur South Gate ki taraf divert karein.",
                "actions": [
                    {
                        "id": "act-1",
                        "action_type": "restrict",
                        "edge_id": primary_congested_edge,
                        "target_node_id": "exit-n",
                        "title": f"Restrict / Close Inflow on {primary_location} ({primary_congested_edge})",
                        "instruction": f"Close corridor {primary_congested_edge} to prevent further pedestrian queue compression into junction.",
                        "expected_outcome": "Stops arrival surge and limits maximum corridor density.",
                    },
                    {
                        "id": "act-2",
                        "action_type": "open_bypass",
                        "edge_id": primary_congested_edge,
                        "target_node_id": "exit-n",
                        "title": "Open North Exit Relief Bypass (exit-n)",
                        "instruction": "Open auxiliary North Exit turnstiles (capacity 2,000/hr) and guide crowd through northern concourse.",
                        "expected_outcome": "Relieves western pressure by evacuating up to 2,000 people/hour.",
                    },
                    {
                        "id": "act-3",
                        "action_type": "divert",
                        "edge_id": primary_congested_edge,
                        "target_node_id": "exit-sw",
                        "title": "Divert West Flow to South-West Exit (exit-sw)",
                        "instruction": "Deploy stewards to guide West concourse visitors towards South-West Exit (exit-sw).",
                        "expected_outcome": "Disperses up to 900 people/hour through secondary southwest gate.",
                    },
                    {
                        "id": "act-4",
                        "action_type": "divert",
                        "edge_id": primary_congested_edge,
                        "target_node_id": "gate-s",
                        "title": "Divert Concourse Flow to South Gate (gate-s)",
                        "instruction": "Deploy crowd stewards to guide incoming or exiting visitors towards South Gate.",
                        "expected_outcome": "Balances venue footprint and avoids secondary bottleneck formation.",
                    },
                ],
                "restricted_edges": list(sim_state.restricted_edges.keys()),
            }
