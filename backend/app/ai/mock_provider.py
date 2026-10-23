from __future__ import annotations

"""
MockAIProvider — generates realistic mock analysis and robust parameter extraction without external APIs.
Used when API tokens are unavailable or in test/offline modes.
Extracts arbitrary natural-language scenarios, incidents, camera observations,
and resolves locations against the venue graph.
"""

import re
import time
from datetime import datetime, timezone
from typing import Any

from app.ai.provider import AIProvider
from app.ai.schemas import (
    ScenarioParseResult, ParsedScenario, SafetyAnalysis,
    EntryDistributionItem, EventTimingInfo, CrowdGroupInfo,
    IncidentRecord,
)
from app.graph.resolver import resolve_location
from app.services.venue_service import get_venue
from app.core.logging import get_logger

log = get_logger(__name__)


class MockAIProvider(AIProvider):
    """
    Deterministic AI provider.
    Extracts structured scenarios, provenance, and generalized incidents from text.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def is_available(self) -> bool:
        return True

    async def parse_scenario(self, text: str) -> ScenarioParseResult:
        log.info("MockAI: parsing scenario text (%d chars)", len(text))
        lower = text.lower()
        notes: list[str] = []
        missing_fields: list[str] = []
        unresolved_locations: list[str] = []
        clarifications: list[str] = []
        provenance: dict[str, str] = {}

        graph = get_venue("venue-stadium-a")

        # ── 1. Crowd Size ───────────────────────────────────────────────────────
        crowd_size = 20000
        size_match = re.search(r"([\d,]+)\s*(?:people|attendees|persons|visitors|crowd|spectators)", text, re.I)
        if size_match:
            crowd_size = int(size_match.group(1).replace(",", ""))
            provenance["crowdSize"] = "explicit"
            notes.append(f"Explicit crowd size: {crowd_size:,}")
        else:
            provenance["crowdSize"] = "default"
            missing_fields.append("crowd_size")
            notes.append("Crowd size not stated — defaulted to 20,000")

        # ── 2. Event Timing ─────────────────────────────────────────────────────
        time_match = re.search(r"(\d{1,2}(?::\d{2})?)\s*(am|pm)\b", text, re.I)
        if time_match:
            raw_time = time_match.group(1)
            is_pm = time_match.group(2).lower() == "pm"
            if ":" in raw_time:
                h_str, m_str = raw_time.split(":")
                h, m = int(h_str), int(m_str)
            else:
                h, m = int(raw_time), 0
            if is_pm and h < 12:
                h += 12
            elif not is_pm and h == 12:
                h = 0
            start_min = h * 60 + m
            provenance["timing"] = "explicit"
            notes.append(f"Explicit event start time: {h:02d}:{m:02d}")
        else:
            start_min = 19 * 60  # Documented standard default: 19:00
            provenance["timing"] = "default"
            missing_fields.append("event_start_time")
            clarifications.append("Event start time was not specified; standard default 19:00 (Evening) applied.")
            notes.append("Event start time missing — defaulted to 19:00 (labeled as default)")

        # ── 3. Entry Distribution ───────────────────────────────────────────────
        has_gate_specs = False
        entry_dist = [
            EntryDistributionItem(gateId="gate-e", fraction=0.55),
            EntryDistributionItem(gateId="gate-w", fraction=0.30),
            EntryDistributionItem(gateId="gate-s", fraction=0.15),
        ]

        # Check if gate mentions are positive ingress/surge vs alternative/less crowded
        east_is_less_crowded = bool(re.search(r"east gate[^\.\,;]*?(?:less crowded|clear|empty|alternative|uncongested|available)", lower))
        west_is_surge = bool(re.search(r"(?:surge|rush|crowd|moving|congregated|heavy|congested|from)[^\.\,;]*?west", lower) or ("west gate" in lower and not bool(re.search(r"west gate[^\.\,;]*?(?:less crowded|clear|empty)", lower))))

        # Check for explicit percentages in text
        gate_pcts = re.findall(r"(\d{1,3})%\s*(?:arrive|enter|use|through)?\s*(?:the\s+)?([a-z]+(?:\s+gate)?)", lower)
        if gate_pcts:
            has_gate_specs = True
            provenance["entryDistribution"] = "explicit"
            notes.append("Explicit gate distribution percentages parsed")

        elif west_is_surge and east_is_less_crowded:
            entry_dist[0].fraction = 0.20
            entry_dist[1].fraction = 0.65
            entry_dist[2].fraction = 0.15
            has_gate_specs = True
            provenance["entryDistribution"] = "inferred"
            notes.append("Primary crowd concentration: West corridor/gate; East Gate identified as secondary/alternative")
        elif "east gate" in lower and "west gate" in lower:
            has_gate_specs = True
            provenance["entryDistribution"] = "explicit"
            notes.append("Explicit gate routing mentioned (East & West gates)")
        elif "west gate" in lower or "from the west" in lower or "western" in lower:
            entry_dist[0].fraction = 0.25
            entry_dist[1].fraction = 0.60
            entry_dist[2].fraction = 0.15
            has_gate_specs = True
            provenance["entryDistribution"] = "explicit"
            notes.append("Primary entry: West Gate (explicitly identified)")
        elif "east gate" in lower and not east_is_less_crowded:
            entry_dist[0].fraction = 0.60
            entry_dist[1].fraction = 0.25
            entry_dist[2].fraction = 0.15
            has_gate_specs = True
            provenance["entryDistribution"] = "explicit"
            notes.append("Primary entry: East Gate (explicitly identified)")


        if not has_gate_specs:
            provenance["entryDistribution"] = "default"
            missing_fields.append("entry_distribution")
            clarifications.append("Gate arrival distribution was not specified; default multi-gate allocation applied.")
            notes.append("Gate distribution missing — balanced default applied across gates")

        # ── 4. Event Name / Type ────────────────────────────────────────────────
        name = "Event"
        if any(w in lower for w in ["music festival", "festival", "fair"]):
            name = "Music Festival"
            notes.append("Event type: Music Festival")
        elif any(w in lower for w in ["concert", "gig", "show", "performance"]):
            name = "Concert"
            notes.append("Event type: Concert")
        elif any(w in lower for w in ["match", "game", "sport", "ipl", "football", "tournament"]):
            name = "Sporting Event"
            notes.append("Event type: Sporting Event")

        # ── 5. Generalized Incident & Observation Extraction ────────────────────
        incidents: list[IncidentRecord] = []
        inc_counter = 1
        has_medical_emergency = False
        seen_incident_keys: set[str] = set()

        # Directive and query patterns: instructions or questions from operators should not be parsed as venue incidents
        directive_patterns = [
            r"^(?:identify|assess|recommend|specify|evaluate|determine|analyze|advise|check|investigate|examine|estimate|plan)\b",
            r"\b(?:what\s+(?:camera|feeds|information|strategy|actions|exits|routes)|how\s+to\s+isolate|before\s+selecting|in\s+order\s+to)\b",
            r"\b(?:capacities\s+are\s+unknown|capacity\s+is\s+unknown|unknown\s+capacity)\b",
            r"\b(?:fire-service\s+confirmation|exit-status\s+information)\b",
        ]

        # Break text into discrete sentences first (never split inside lists on commas)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
        focal_location: str | None = None

        def _find_clause_landmark(clause_text: str, current_focal: str | None) -> str | None:
            clow = clause_text.lower()
            landmarks = [
                (r"\b(?:medical\s+access\s+corridor|medical\s+corridor|stage[- ]to[- ]medical)\b", "Medical Access Corridor"),
                (r"\b(?:main\s+entrance\s+corridor|east\s+gate\s+corridor|main\s+entry\s+corridor)\b", "Main Entrance Corridor"),
                (r"\b(?:west\s+entrance\s+corridor|west\s+gate\s+corridor)\b", "West Entrance Corridor"),
                (r"\b(?:south\s+entrance\s+corridor|south\s+gate\s+corridor)\b", "South Entrance Corridor"),
                (r"\b(?:north\s+corridor)\b", "North Corridor"),
                (r"\b(?:central\s+corridor)\b", "Central Corridor"),
                (r"\b(?:nw\s+corridor)\b", "NW Corridor"),
                (r"\b(?:ne\s+corridor)\b", "NE Corridor"),
                (r"\b(?:sw\s+corridor)\b", "SW Corridor"),
                (r"\b(?:se\s+corridor)\b", "SE Corridor"),
                (r"\b(?:front[- ]stage|main\s+stage|stage(?:\s+area)?)\b", "Main Stage"),
                (r"\b(?:medical\s+station|medical\s+tent|first\s+aid(?:\s+station)?|first\s+aid|infirmary)\b", "Medical Station"),
                (r"\b(?:north\s+food(?:\s+court)?)\b", "North Food Court"),
                (r"\b(?:south\s+food(?:\s+court)?)\b", "South Food Court"),
                (r"\b(?:north\s+exit)\b", "North Exit"),
                (r"\b(?:south[- ]west\s+exit|sw\s+exit)\b", "SW Exit"),
                (r"\b(?:south[- ]east\s+exit|se\s+exit)\b", "SE Exit"),
                (r"\b(?:main\s+entrance|east\s+gate|primary\s+east\s+entrance)\b", "East Gate"),
                (r"\b(?:west\s+gate|primary\s+west\s+entrance)\b", "West Gate"),
                (r"\b(?:south\s+gate|secondary\s+south\s+entrance)\b", "South Gate"),
                (r"\b(?:north\s+junction)\b", "North Junction"),
                (r"\b(?:south\s+junction)\b", "South Junction"),
                (r"\b(?:east\s+junction)\b", "East Junction"),
                (r"\b(?:west\s+junction)\b", "West Junction"),
            ]
            for pat, name in landmarks:
                if re.search(pat, clow):
                    return name

            # Prepositional location
            loc_m = re.search(r"\b(?:near|at|around|along|in|by|toward)\s+(?:the\s+)?([a-zA-Z0-9\- ']+?)(?:'s|\bwhile\b|\band\b|\brequiring\b|,|\.|$)", clause_text, re.I)
            if loc_m:
                clean = loc_m.group(1).strip()
                clean = re.sub(r"['’]s?\s+electrical(?:\s+equipment)?", "", clean, flags=re.I).strip()
                return clean

            # Passive location
            pass_m = re.search(r"\b([a-zA-Z0-9\- ]*(?:corridor|exit|gate|path|walkway|route))\s+(?:is|was|are|has\s+been)\b", clause_text, re.I)
            if pass_m:
                return pass_m.group(1).strip()

            return current_focal

        for sentence in sentences:
            slow = sentence.lower()

            # If the entire sentence is an operator directive or capability query, record in clarifications/notes
            if any(re.search(pat, slow, re.I) for pat in directive_patterns):
                clarifications.append(f"Operator instruction noted: {sentence}")
                continue

            # Split narrative sentences into clauses (comma or semicolon separated)
            clauses = [c.strip() for c in re.split(r"[;]|,\s*(?:and\s+)?", sentence) if len(c.strip()) > 5]
            if not clauses:
                clauses = [sentence]

            for clause in clauses:
                clow = clause.lower()

                # Skip subclauses that are directives
                if any(re.search(pat, clow, re.I) for pat in directive_patterns):
                    continue

                # 5a. Corridor / Exit restriction / blockage (active or passive)
                if re.search(r"\b(?:restrict(?:ed|ing)?|close(?:d|ing)?|block(?:ed|age)?|shut|narrow(?:ed)?)\s+(?:the\s+)?([a-zA-Z0-9\- ]*corridor|[a-zA-Z0-9\- ]*path|[a-zA-Z0-9\- ]*walkway|[a-zA-Z0-9\- ]*exit|[a-zA-Z0-9\- ]*route)\b", clow) or re.search(r"\b(?:corridor|exit|gate|path|walkway|route)\s+(?:is|was|are|has\s+been)\s+(?:closed|blocked|restricted|shut|narrowed)\b", clow) or "restricted movement" in clow or "restricted corridor" in clow:
                    corr_str = _find_clause_landmark(clause, focal_location) or "corridor"
                    corr_str = re.sub(r"\s+(?:to\s+emergency|personnel)$", "", corr_str, flags=re.I).strip()
                    res = resolve_location(corr_str, graph)
                    key = f"restricted-corridor:{res.resolved_edge_id or res.resolved_node_id or corr_str}"
                    if key not in seen_incident_keys:
                        seen_incident_keys.add(key)
                        inc = IncidentRecord(
                            id=f"inc-{inc_counter}",
                            type="restricted-corridor",
                            description=clause.strip(),
                            reported_location=corr_str,
                            resolved_node_id=res.resolved_node_id,
                            resolved_edge_id=res.resolved_edge_id,
                            unresolved=not res.is_resolved,
                            severity="moderate",
                            source="staff" if "staff" in clow else "camera_observation",
                            verification_status="observed",
                            at_minute=0.0,
                            operational_constraints=["restricted_movement", "capacity_reduced"],
                            recommended_response=f"Manage pedestrian rerouting around restricted corridor '{corr_str}'.",
                            current_status="active",
                        )
                        incidents.append(inc)
                        inc_counter += 1
                        focal_location = corr_str
                        notes.append(f"Preserved Corridor Restriction at '{corr_str}' (resolved: {res.resolved_edge_id or res.resolved_node_id or 'UNRESOLVED'})")

                # 5b. Medical emergency
                elif re.search(r"\b(?:collapse|collapsed|collapses|heat\s+exhaustion|exhaustion|first\s+aid|cardiac|injured|injury|faint|fainted|unconscious|casualty)\b", clow) or ("medical" in clow and "corridor" not in clow):
                    if not has_medical_emergency:
                        loc_str = _find_clause_landmark(clause, focal_location) or "Medical Station"
                        loc_str = re.sub(r"\s+(?:area|requiring|assistance|personnel)$", "", loc_str, flags=re.I).strip()
                        res = resolve_location(loc_str, graph)
                        key = f"medical:{res.resolved_node_id or loc_str}"
                        if key not in seen_incident_keys:
                            seen_incident_keys.add(key)
                            inc = IncidentRecord(
                                id=f"inc-{inc_counter}",
                                type="medical",
                                description=clause.strip(),
                                reported_location=loc_str,
                                resolved_node_id=res.resolved_node_id,
                                resolved_edge_id=res.resolved_edge_id,
                                unresolved=not res.is_resolved,
                                severity="emergency",
                                source="security" if "security" in clow else "user_report",
                                verification_status="reported",
                                at_minute=0.0,
                                operational_constraints=["medical_access_required", "responder_corridor_priority"],
                                recommended_response=f"Dispatch medical responders to {loc_str}; verify clear access route.",
                                current_status="active",
                            )
                            incidents.append(inc)
                            inc_counter += 1
                            has_medical_emergency = True
                            focal_location = loc_str
                            notes.append(f"Preserved Medical Emergency at '{loc_str}' (resolved: {res.resolved_node_id or 'UNRESOLVED'})")

                # 5c. Fire / Smoke / Electrical / Hazard
                elif re.search(r"\b(?:smoke|fire|flames|electrical(?:\s+equipment|\s+fire)?|explosion|blast|chemical|gas\s+leak|burning|blackout|hazard|power\s+(?:outage|glitch|failure))\b", clow):
                    loc_str = _find_clause_landmark(clause, focal_location) or "Main Stage"
                    focal_location = loc_str
                    res = resolve_location(loc_str, graph)
                    key = f"fire:{res.resolved_node_id or loc_str}"
                    if key not in seen_incident_keys:
                        seen_incident_keys.add(key)
                        inc = IncidentRecord(
                            id=f"inc-{inc_counter}",
                            type="fire" if any(w in clow for w in ["smoke", "fire", "flames", "electrical", "explosion", "gas"]) else "structural",
                            description=clause.strip(),
                            reported_location=loc_str,
                            resolved_node_id=res.resolved_node_id,
                            resolved_edge_id=res.resolved_edge_id,
                            unresolved=not res.is_resolved,
                            severity="emergency" if any(w in clow for w in ["fire", "smoke", "explosion"]) else "high",
                            source="security" if "security" in clow else "user_report",
                            verification_status="reported",
                            at_minute=0.0,
                            operational_constraints=["hazard_containment", "evacuation_priority"],
                            recommended_response=f"Isolate hazard zone at '{loc_str}', isolate power, and establish perimeter.",
                            current_status="active",
                        )
                        incidents.append(inc)
                        inc_counter += 1
                        notes.append(f"Preserved Hazard Incident at '{loc_str}' (resolved: {res.resolved_node_id or 'UNRESOLVED'})")

                # 5d. Congestion / Compression
                elif re.search(r"\b(?:congestion|congested|crowd\s+compression|compression|bottleneck|crowding|gate\s+crush|crush|jam|overcrowd)\b", clow):
                    if "nearest corridor" in clow:
                        loc_str = f"corridor near {focal_location}" if focal_location else "central corridor"
                    else:
                        loc_str = _find_clause_landmark(clause, focal_location) or "Central Corridor"

                    res = resolve_location(loc_str, graph)
                    key = f"congestion:{res.resolved_edge_id or res.resolved_node_id or loc_str}"
                    if key not in seen_incident_keys:
                        seen_incident_keys.add(key)
                        inc = IncidentRecord(
                            id=f"inc-{inc_counter}",
                            type="congestion",
                            description=clause.strip(),
                            reported_location=loc_str,
                            resolved_node_id=res.resolved_node_id,
                            resolved_edge_id=res.resolved_edge_id,
                            unresolved=not res.is_resolved,
                            severity="high" if any(w in clow for w in ["compression", "crush", "gate crush"]) else "moderate",
                            source="camera_observation" if "camera" in clow else "security",
                            verification_status="observed",
                            at_minute=0.0,
                            operational_constraints=["congestion", "queue_management"],
                            recommended_response=f"Manage inflow metering and open bypass lanes around '{loc_str}'.",
                            current_status="active",
                        )
                        incidents.append(inc)
                        inc_counter += 1
                        notes.append(f"Preserved Congestion at '{loc_str}' (resolved: {res.resolved_edge_id or res.resolved_node_id or 'UNRESOLVED'})")

                # 5e. Crowd movement / Observation / Surge
                elif re.search(r"\b(?:increasing\s+(?:crowd\s+)?density|moving\s+toward|investigate|crowd\s+surge|panicking|surging|gathering|density\s+surge|high\s+density|elevated\s+crowd\s+density)\b", clow):
                    if "fire location" in clow or "hazard location" in clow or "suspected" in clow:
                        loc_str = focal_location or "Main Stage"
                    else:
                        loc_str = _find_clause_landmark(clause, focal_location) or "Main Stage"

                    res = resolve_location(loc_str, graph)
                    key = f"observation:{res.resolved_node_id or res.resolved_edge_id or loc_str}"
                    if key not in seen_incident_keys:
                        seen_incident_keys.add(key)
                        inc = IncidentRecord(
                            id=f"inc-{inc_counter}",
                            type="observation",
                            description=clause.strip(),
                            reported_location=loc_str,
                            resolved_node_id=res.resolved_node_id,
                            resolved_edge_id=res.resolved_edge_id,
                            unresolved=not res.is_resolved,
                            severity="high" if "surge" in clow else "moderate",
                            source="camera_observation",
                            verification_status="observed",
                            at_minute=0.0,
                            operational_constraints=["density_monitoring"],
                            recommended_response=f"Monitor crowd movement and deploy stewards to redirect flow at '{loc_str}'.",
                            current_status="active",
                        )
                        incidents.append(inc)
                        inc_counter += 1
                        notes.append(f"Preserved Density Observation at '{loc_str}' (resolved: {res.resolved_node_id or res.resolved_edge_id or 'UNRESOLVED'})")


        # Compile unresolved locations
        for inc in incidents:
            if inc.unresolved and inc.reported_location not in unresolved_locations:
                unresolved_locations.append(inc.reported_location)

        # ── 6. Crowd Groups (scaled to exact crowd_size) ───────────────────────
        groups = [
            CrowdGroupInfo(
                id="g-main",
                name="Front-of-stage crowd",
                size=int(crowd_size * 0.55),
                entryGateId="gate-e",
                destinationNodeId="stage",
                arrivalStartMin=-60,
                arrivalEndMin=0,
            ),
            CrowdGroupInfo(
                id="g-west",
                name="West wing audience",
                size=int(crowd_size * 0.30),
                entryGateId="gate-w",
                destinationNodeId="stage",
                arrivalStartMin=-50,
                arrivalEndMin=10,
            ),
            CrowdGroupInfo(
                id="g-facilities",
                name="Plaza & food court attendees",
                size=crowd_size - int(crowd_size * 0.55) - int(crowd_size * 0.30),
                entryGateId="gate-s",
                destinationNodeId="food-n",
                arrivalStartMin=-40,
                arrivalEndMin=20,
            ),
        ]

        parsed = ParsedScenario(
            id=f"scenario-{int(time.time())}",
            name=name,
            venueId="venue-stadium-a",
            crowdSize=crowd_size,
            crowdSize_origin=provenance.get("crowdSize", "explicit"),
            entryDistribution=entry_dist,
            entryDistribution_origin=provenance.get("entryDistribution", "default"),
            crowdGroups=groups,
            timing=EventTimingInfo(
                startMinutesOfDay=start_min,
                durationMin=180,
                arrivalPattern="surge",
                departurePattern="surge",
            ),
            timing_origin=provenance.get("timing", "default"),
            entryRate=min(max(crowd_size // 30, 300), 1500),
            exitRate=min(max(crowd_size // 20, 500), 2000),
            incidents=incidents,
            parameter_provenance=provenance,
            missing_fields=missing_fields,
            unresolved_locations=unresolved_locations,
            clarifications=clarifications,
            naturalLanguage=text,
            notes=notes,
        )

        return ScenarioParseResult(
            success=True,
            parsed=parsed,
            stage="ready",
            notes=notes,
            missing_fields=missing_fields,
            unresolved_locations=unresolved_locations,
            clarifications=clarifications,
            raw_text=text,
            provider="mock",
        )

    async def analyze_safety(
        self,
        metrics: dict[str, Any],
        safety_state: dict[str, Any],
        sim_time_min: float,
        sim_status: str,
        emergency: dict | None = None,
        route_changes: list[dict] | None = None,
    ) -> SafetyAnalysis:
        """Generate safety analysis grounded in deterministic metrics and incidents."""
        risk_level = safety_state.get("riskLevel", "low")
        risk_score = safety_state.get("riskScore", 0)
        bottlenecks = safety_state.get("bottlenecks", [])
        people = metrics.get("peopleCount", 0)
        density = metrics.get("avgDensity", 0.0)
        flow = metrics.get("flowRate", 0.0)
        time_to_critical = safety_state.get("timeToCriticalMin")

        if emergency and emergency.get("active"):
            em_type = emergency.get("type", "emergency").upper()
            em_loc = emergency.get("location", "Venue")
            return SafetyAnalysis(
                summary=f"CRITICAL INCIDENT: {em_type} reported at {em_loc}. Emergency routing and access controls active.",
                risk_explanation=(
                    f"A confirmed {em_type} incident is active at {em_loc}. "
                    f"Affected route segments are closed or restricted to clear path for emergency teams. "
                    f"Active crowd is {people:,} with system risk score {risk_score}/100."
                ),
                affected_locations=[em_loc],
                contributing_factors=[
                    f"Active {em_type} event at {em_loc}",
                    "Restricted corridor traversal for medical/emergency access",
                    f"Congestion redirected around {em_loc}",
                ],
                recommended_action=(
                    f"Deploy on-site responders to {em_loc}. Maintain clear corridor along medical access route "
                    f"and redirect non-emergency pedestrian flow away from the affected zone."
                ),
                urgency="emergency",
                supporting_metrics={
                    "risk_score": risk_score,
                    "people_count": people,
                    "avg_density": density,
                    "incident_location": em_loc,
                },
                confidence="high",
            )

        if bottlenecks:
            bn = bottlenecks[0]
            loc = bn.get("location", "Unknown location")
            util_pct = round(bn.get("capacityUtilization", 0) * 100)
            ttc_str = f" Predicted critical in {time_to_critical:.0f} min." if time_to_critical else ""
            return SafetyAnalysis(
                summary=f"Bottleneck detected at {loc} operating at {util_pct}% capacity utilization.",
                risk_explanation=(
                    f"Flow accumulation at {loc} has reached {bn.get('currentDensity', 0):.1%} density, "
                    f"exceeding safe operational threshold. System risk score is {risk_score}/100.{ttc_str}"
                ),
                affected_locations=[loc],
                contributing_factors=[
                    f"High localized density ({bn.get('currentDensity', 0):.1%})",
                    f"Capacity utilization at {util_pct}%",
                    "Outflow rate lower than arrival rate",
                ],
                recommended_action=bn.get("recommendedAction", "Redirect arrival flow to alternative corridors.") + ttc_str,
                urgency=risk_level if risk_level in ("low", "moderate", "high", "critical", "emergency") else "moderate",
                supporting_metrics={
                    "capacity_utilization": bn.get("capacityUtilization"),
                    "current_density": bn.get("currentDensity"),
                    "risk_score": risk_score,
                    "flow_rate": flow,
                },
                confidence="high" if risk_level in ("critical", "high") else "medium",
            )

        return SafetyAnalysis(
            summary="Crowd flow conditions are within normal safe parameters.",
            risk_explanation=(
                f"All corridors operate below congestion thresholds. Active crowd count is {people:,} "
                f"with average density {density:.1%}. Risk score is {risk_score}/100 with no active bottlenecks."
            ),
            affected_locations=[],
            contributing_factors=["All corridors below capacity", "Normal flow rates across gates"],
            recommended_action="Continue routine perimeter monitoring and gate flow supervision.",
            urgency="low",
            supporting_metrics={
                "people_count": people,
                "avg_density": density,
                "risk_score": risk_score,
                "flow_rate": flow,
            },
            confidence="high",
        )
