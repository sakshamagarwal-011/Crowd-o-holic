from __future__ import annotations

"""Ollama-backed local GPU provider for scenario parsing and safety analysis."""

import json
import re
from typing import Any

import httpx

from app.ai.mock_provider import MockAIProvider
from app.ai.prompts import (
    SAFETY_SYSTEM_PROMPT,
    SAFETY_USER_PROMPT_TEMPLATE,
    SCENARIO_SYSTEM_PROMPT,
    SCENARIO_USER_PROMPT_TEMPLATE,
)
from app.ai.provider import AIProvider
from app.ai.schemas import (
    ParsedScenario, SafetyAnalysis, ScenarioParseResult,
    IncidentRecord, EntryDistributionItem, EventTimingInfo, CrowdGroupInfo,
)
from app.graph.resolver import resolve_location
from app.services.venue_service import get_venue
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


def _extract_json(content: str) -> dict[str, Any] | None:
    """Extract JSON object from potentially noisy model output, stripping thinking tags."""
    content = content.strip()
    content = re.sub(r"<think>[\s\S]*?</think>", "", content, flags=re.IGNORECASE).strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if match:
        content = match.group(1).strip()
    start = content.find("{")
    if start < 0:
        return None
    depth = 0
    for index, char in enumerate(content[start:], start=start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    value = json.loads(content[start:index + 1])
                    return value if isinstance(value, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def _ensure_list(val: Any) -> list[str]:
    """Ensure value is a list of strings."""
    if isinstance(val, list):
        return [str(x) for x in val if x is not None]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []


class OllamaAIProvider(AIProvider):

    """Uses local Ollama HTTP API with GPU acceleration (RTX 3050) and falls back to deterministic mock AI."""

    def __init__(self) -> None:
        self._mock = MockAIProvider()

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=1.5) as client:
                r = client.get(f"{settings.ollama_base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def _complete(self, system: str, user: str, temperature: float) -> str:
        url = f"{settings.ollama_base_url}/api/chat"
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")
        if not isinstance(content, str) or not content:
            raise ValueError("Ollama returned empty response")
        return content

    async def parse_scenario(self, text: str) -> ScenarioParseResult:
        try:
            content = await self._complete(
                SCENARIO_SYSTEM_PROMPT,
                SCENARIO_USER_PROMPT_TEMPLATE.format(text=text),
                temperature=0.1,
            )
            data = _extract_json(content)
            if data is None:
                raise ValueError("Ollama returned non-JSON scenario content")

            graph = get_venue("venue-stadium-a")

            # Validate explicit crowd size from raw text
            size_match = re.search(r"([\d,]+)\s*(?:people|attendees|persons|visitors|crowd|spectators)", text, re.I)
            if size_match:
                explicit_size = int(size_match.group(1).replace(",", ""))
                data["crowdSize"] = explicit_size
                data["crowdSize_origin"] = "explicit"
            elif "crowdSize" not in data or not data["crowdSize"]:
                data["crowdSize"] = 20000
                data["crowdSize_origin"] = "default"

            # Check timing provenance
            time_match = re.search(r"(\d{1,2}(?::\d{2})?)\s*(am|pm)\b", text, re.I)
            if not time_match and data.get("timing_origin") != "explicit":
                data["timing_origin"] = "default"
                if "missing_fields" not in data:
                    data["missing_fields"] = []
                if "event_start_time" not in data["missing_fields"]:
                    data["missing_fields"].append("event_start_time")

            # Check gate distribution provenance
            gate_match = re.search(r"\b(?:east|west|south)\s+gate\b", text, re.I)
            if not gate_match and data.get("entryDistribution_origin") != "explicit":
                data["entryDistribution_origin"] = "default"
                if "missing_fields" not in data:
                    data["missing_fields"] = []
                if "entry_distribution" not in data["missing_fields"]:
                    data["missing_fields"].append("entry_distribution")

            # Resolve incidents
            raw_incidents = data.get("incidents", [])
            resolved_incidents: list[IncidentRecord] = []
            unresolved_locations: list[str] = []

            for inc_data in raw_incidents:
                loc_text = inc_data.get("reported_location", "")
                res = resolve_location(loc_text, graph)
                inc = IncidentRecord(
                    id=inc_data.get("id", f"inc-{len(resolved_incidents)+1}"),
                    type=inc_data.get("type", "other"),
                    description=inc_data.get("description", ""),
                    reported_location=loc_text,
                    resolved_node_id=res.resolved_node_id,
                    resolved_edge_id=res.resolved_edge_id,
                    unresolved=not res.is_resolved,
                    severity=inc_data.get("severity", "moderate"),
                    source=inc_data.get("source", "user_report"),
                    verification_status=inc_data.get("verification_status", "reported"),
                    at_minute=float(inc_data.get("at_minute", 0.0)),
                    operational_constraints=inc_data.get("operational_constraints", []),
                    recommended_response=inc_data.get("recommended_response", ""),
                    current_status=inc_data.get("current_status", "active"),
                )
                resolved_incidents.append(inc)
                if not res.is_resolved:
                    unresolved_locations.append(loc_text)

            # If model missed key incidents, augment with deterministic fallback
            if not resolved_incidents and any(w in text.lower() for w in ["collapse", "medical", "restricted", "congestion", "fire", "smoke"]):
                mock_res = await self._mock.parse_scenario(text)
                if mock_res.parsed:
                    resolved_incidents = mock_res.parsed.incidents
                    unresolved_locations = mock_res.parsed.unresolved_locations

            entry_dist_raw = data.get("entryDistribution")
            entry_items: list[EntryDistributionItem] = []
            if isinstance(entry_dist_raw, list):
                for item in entry_dist_raw:
                    if isinstance(item, dict) and "gateId" in item:
                        entry_items.append(EntryDistributionItem(
                            gateId=str(item["gateId"]),
                            fraction=float(item.get("fraction", 0.0)),
                        ))
            if not entry_items:
                entry_items = [
                    EntryDistributionItem(gateId="gate-e", fraction=0.34),
                    EntryDistributionItem(gateId="gate-w", fraction=0.33),
                    EntryDistributionItem(gateId="gate-s", fraction=0.33),
                ]

            groups_raw = data.get("crowdGroups")
            group_items: list[CrowdGroupInfo] = []
            if isinstance(groups_raw, list):
                for item in groups_raw:
                    if isinstance(item, dict):
                        group_items.append(CrowdGroupInfo(
                            id=str(item.get("id", f"g-{len(group_items)+1}")),
                            name=str(item.get("name", "Group")),
                            size=int(item.get("size", 1000)),
                            entryGateId=str(item.get("entryGateId", "gate-w")),
                            destinationNodeId=str(item.get("destinationNodeId", "stage")),
                            arrivalStartMin=float(item.get("arrivalStartMin", -60)),
                            arrivalEndMin=float(item.get("arrivalEndMin", 0)),
                        ))

            timing_dict = data.get("timing") if isinstance(data.get("timing"), dict) else {"startMinutesOfDay": 1140}

            parsed = ParsedScenario(
                id=str(data.get("id", "scenario-ollama")),
                name=str(data.get("name", "Event")),
                venueId="venue-stadium-a",
                crowdSize=int(data["crowdSize"]),
                crowdSize_origin=str(data.get("crowdSize_origin", "explicit")),
                entryDistribution=entry_items,
                entryDistribution_origin=str(data.get("entryDistribution_origin", "default")),
                crowdGroups=group_items,
                timing=EventTimingInfo(**timing_dict),
                timing_origin=str(data.get("timing_origin", "default")),
                entryRate=float(data.get("entryRate", 500.0)),
                exitRate=float(data.get("exitRate", 800.0)),
                incidents=resolved_incidents,
                parameter_provenance={
                    "crowdSize": str(data.get("crowdSize_origin", "explicit")),
                    "timing": str(data.get("timing_origin", "default")),
                    "entryDistribution": str(data.get("entryDistribution_origin", "default")),
                },
                missing_fields=_ensure_list(data.get("missing_fields")),
                unresolved_locations=unresolved_locations,
                clarifications=_ensure_list(data.get("clarifications")),
                naturalLanguage=text,
                notes=_ensure_list(data.get("notes")) + [f"Local AI GPU Provider: Ollama ({settings.ollama_model})"],
            )


            return ScenarioParseResult(
                success=True,
                parsed=parsed,
                stage="ready",
                notes=parsed.notes,
                missing_fields=parsed.missing_fields,
                unresolved_locations=parsed.unresolved_locations,
                clarifications=parsed.clarifications,
                raw_text=text,
                provider="ollama",
            )
        except Exception as exc:
            log.warning("Ollama local scenario parsing failed (%s: %s); falling back to mock provider", type(exc).__name__, exc)
            fallback = await self._mock.parse_scenario(text)
            fallback.provider = "mock-fallback"
            fallback.error = f"Ollama request failed ({type(exc).__name__}): {str(exc)}"
            if fallback.notes is not None:
                fallback.notes.append(f"AI Provider Notice: Ollama local model failed ({type(exc).__name__}). Deterministic fallback applied.")
            return fallback

    async def analyze_safety(
        self,
        metrics: dict[str, Any],
        safety_state: dict[str, Any],
        sim_time_min: float,
        sim_status: str,
        emergency: dict | None = None,
        route_changes: list[dict] | None = None,
    ) -> SafetyAnalysis:
        bottlenecks = safety_state.get("bottlenecks", [])
        lines: list[str] = []
        for bn in bottlenecks[:3]:
            time_to_critical = bn.get("timeToCriticalMin")
            ttc_str = f", time-to-critical {time_to_critical:.0f} min" if time_to_critical else ""
            lines.append(
                f"- {bn.get('location')}: density {bn.get('currentDensity', 0):.0%}, "
                f"capacity utilization {bn.get('capacityUtilization', 0):.0%}, "
                f"risk {bn.get('risk')}{ttc_str}. Action: {bn.get('recommendedAction', 'None')}"
            )
        emergency_status = "None"
        if emergency and emergency.get("active"):
            emergency_status = f"ACTIVE: {emergency.get('type')} at {emergency.get('location')} ({emergency.get('summary')})"

        time_to_critical = safety_state.get("timeToCriticalMin")
        prompt = SAFETY_USER_PROMPT_TEMPLATE.format(
            sim_time_min=sim_time_min,
            people_count=metrics.get("peopleCount", 0),
            sim_status=sim_status,
            avg_density=metrics.get("avgDensity", 0.0),
            flow_rate=metrics.get("flowRate", 0.0),
            avg_speed=metrics.get("avgSpeed", 0.0),
            capacity_utilization=metrics.get("capacityUtilization", 0.0),
            queue_growth=metrics.get("queueGrowth", 0.0),
            risk_score=safety_state.get("riskScore", 0),
            risk_level=safety_state.get("riskLevel", "low"),
            ttc=f"{time_to_critical:.0f} min" if time_to_critical else "N/A",
            bn_count=len(bottlenecks),
            bottleneck_details="\n".join(lines) if lines else "  None",
            emergency_status=emergency_status,
            route_changes="; ".join(change.get("reason", "") for change in (route_changes or [])[:2]) or "None",
        )
        try:
            content = await self._complete(SAFETY_SYSTEM_PROMPT, prompt, temperature=0.2)
            data = _extract_json(content)
            if data is None:
                raise ValueError("Ollama returned non-JSON safety content")
            return SafetyAnalysis(**{key: value for key, value in data.items() if key in SafetyAnalysis.model_fields})
        except Exception as exc:
            log.warning("Ollama safety analysis failed (%s: %s); using fallback mock provider", type(exc).__name__, exc)
            fallback = await self._mock.analyze_safety(metrics, safety_state, sim_time_min, sim_status, emergency, route_changes)
            return fallback
