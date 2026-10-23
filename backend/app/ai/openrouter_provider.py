from __future__ import annotations

"""OpenRouter-backed provider for scenario parsing and safety explanations."""

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
OPENROUTER_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


def _extract_json(content: str) -> dict[str, Any] | None:
    """Accept either raw JSON or a JSON fenced code block from a model, stripping reasoning tags."""
    content = content.strip()
    # Strip thinking tags from reasoning models
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


class OpenRouterAIProvider(AIProvider):
    """Uses the OpenRouter chat-completions API and safely falls back to mock AI."""

    def __init__(self) -> None:
        self._mock = MockAIProvider()

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def is_available(self) -> bool:
        return bool(settings.openrouter_api_key)

    async def _complete(self, system: str, user: str, max_tokens: int, temperature: float) -> str:
        if not settings.openrouter_api_key:
            raise RuntimeError("OpenRouter API key is not configured")
        payload = {
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "X-Title": settings.app_name,
        }
        async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
            response = await client.post(OPENROUTER_COMPLETIONS_URL, json=payload, headers=headers)
            response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("OpenRouter returned no text content")
        return content

    async def parse_scenario(self, text: str) -> ScenarioParseResult:
        try:
            content = await self._complete(
                SCENARIO_SYSTEM_PROMPT,
                SCENARIO_USER_PROMPT_TEMPLATE.format(text=text),
                max_tokens=2048,
                temperature=0.1,
            )
            data = _extract_json(content)
            if data is None:
                raise ValueError("OpenRouter returned non-JSON scenario content")

            graph = get_venue("venue-stadium-a")

            # Validate explicit crowd size from raw text to prevent model hallucination/override
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

            # Process and resolve incidents
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

            # If model missed key incidents mentioned in text, augment with mock extractor
            if not resolved_incidents and any(w in text.lower() for w in ["collapse", "medical", "restricted", "congestion"]):
                mock_res = await self._mock.parse_scenario(text)
                if mock_res.parsed:
                    resolved_incidents = mock_res.parsed.incidents
                    unresolved_locations = mock_res.parsed.unresolved_locations

            # Create validated ParsedScenario
            parsed = ParsedScenario(
                id=data.get("id", "scenario-ai"),
                name=data.get("name", "Event"),
                venueId="venue-stadium-a",
                crowdSize=int(data["crowdSize"]),
                crowdSize_origin=data.get("crowdSize_origin", "explicit"),
                entryDistribution=[
                    EntryDistributionItem(**item) for item in data.get("entryDistribution", [])
                ] or [
                    EntryDistributionItem(gateId="gate-e", fraction=0.55),
                    EntryDistributionItem(gateId="gate-w", fraction=0.30),
                    EntryDistributionItem(gateId="gate-s", fraction=0.15),
                ],
                entryDistribution_origin=data.get("entryDistribution_origin", "default"),
                crowdGroups=[
                    CrowdGroupInfo(**item) for item in data.get("crowdGroups", [])
                ],
                timing=EventTimingInfo(**(data.get("timing") or {"startMinutesOfDay": 1140})),
                timing_origin=data.get("timing_origin", "default"),
                entryRate=float(data.get("entryRate", 500.0)),
                exitRate=float(data.get("exitRate", 800.0)),
                incidents=resolved_incidents,
                parameter_provenance={
                    "crowdSize": data.get("crowdSize_origin", "explicit"),
                    "timing": data.get("timing_origin", "default"),
                    "entryDistribution": data.get("entryDistribution_origin", "default"),
                },
                missing_fields=data.get("missing_fields", []),
                unresolved_locations=unresolved_locations,
                clarifications=data.get("clarifications", []),
                naturalLanguage=text,
                notes=data.get("notes", []),
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
                provider="openrouter",
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError, RuntimeError) as exc:
            log.warning("OpenRouter scenario parsing failed (%s: %s); falling back to mock provider", type(exc).__name__, exc)
            fallback = await self._mock.parse_scenario(text)
            fallback.provider = "mock-fallback"
            fallback.error = f"OpenRouter upstream request failed ({type(exc).__name__}): {str(exc)}"
            if fallback.notes is not None:
                fallback.notes.append(f"AI Provider Notice: OpenRouter request failed ({type(exc).__name__}). Offline deterministic fallback was applied.")
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
            content = await self._complete(SAFETY_SYSTEM_PROMPT, prompt, max_tokens=600, temperature=0.2)
            data = _extract_json(content)
            if data is None:
                raise ValueError("OpenRouter returned non-JSON safety content")
            return SafetyAnalysis(**{key: value for key, value in data.items() if key in SafetyAnalysis.model_fields})
        except (httpx.HTTPError, KeyError, TypeError, ValueError, RuntimeError) as exc:
            log.warning("OpenRouter safety analysis failed (%s: %s); using fallback mock provider", type(exc).__name__, exc)
            fallback = await self._mock.analyze_safety(metrics, safety_state, sim_time_min, sim_status, emergency, route_changes)
            return fallback
