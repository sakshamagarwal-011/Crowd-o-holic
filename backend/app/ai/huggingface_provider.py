from __future__ import annotations

"""
HuggingFace AI Provider using Qwen/Qwen2.5-7B-Instruct.
Uses client.chat_completion() as required by the spec.
Never exposes HF_TOKEN in logs, exceptions, or API responses.
"""

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from app.ai.provider import AIProvider
from app.ai.schemas import ScenarioParseResult, ParsedScenario, SafetyAnalysis
from app.ai.prompts import (
    SCENARIO_SYSTEM_PROMPT,
    SCENARIO_USER_PROMPT_TEMPLATE,
    SAFETY_SYSTEM_PROMPT,
    SAFETY_USER_PROMPT_TEMPLATE,
)
from app.ai.mock_provider import MockAIProvider
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Lazy import — only loaded if token available
_client = None
_client_initialized = False


def _get_client():
    global _client, _client_initialized
    if _client_initialized:
        return _client
    _client_initialized = True
    try:
        from huggingface_hub import InferenceClient
        token = settings.hf_token
        if not token:
            _client = None
            return None
        _client = InferenceClient(
            model=settings.hf_model,
            token=token,
        )
        log.info("HuggingFace InferenceClient initialized | model=%s", settings.hf_model)
    except Exception:
        log.warning("Failed to initialize HuggingFace client — falling back to mock")
        _client = None
    return _client


def _extract_json(text: str) -> dict | None:
    """Extract JSON object from potentially noisy model output."""
    # Try to find JSON block
    text = text.strip()
    # Check for JSON code block
    code_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_match:
        text = code_match.group(1)
    # Find first { ... }
    start = text.find("{")
    if start == -1:
        return None
    # Find matching closing brace
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


class HuggingFaceAIProvider(AIProvider):
    """
    Real AI provider using Qwen/Qwen2.5-7B-Instruct via HuggingFace Inference API.
    Falls back to MockAIProvider on any failure.
    """

    def __init__(self):
        self._mock = MockAIProvider()

    @property
    def provider_name(self) -> str:
        return "huggingface"

    @property
    def is_available(self) -> bool:
        return bool(settings.hf_token) and _get_client() is not None

    async def parse_scenario(self, text: str) -> ScenarioParseResult:
        client = _get_client()
        if client is None:
            log.warning("HF client not available — using mock for scenario parsing")
            return await self._mock.parse_scenario(text)

        prompt = SCENARIO_USER_PROMPT_TEMPLATE.format(text=text)
        try:
            raw = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.chat_completion(
                        messages=[
                            {"role": "system", "content": SCENARIO_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=1024,
                        temperature=0.1,
                    ),
                ),
                timeout=settings.ai_timeout,
            )
            content = raw.choices[0].message.content
            data = _extract_json(content)
            if data is None:
                raise ValueError("Model returned non-JSON output")

            # Validate with Pydantic
            parsed = ParsedScenario(
                **{k: v for k, v in data.items() if k in ParsedScenario.model_fields},
                naturalLanguage=text,
            )
            notes = data.get("notes", [])
            log.info("HF scenario parsing succeeded | crowd_size=%s", parsed.crowdSize)
            return ScenarioParseResult(
                success=True,
                parsed=parsed,
                stage="ready",
                notes=notes,
                raw_text=text,
                provider="huggingface",
            )

        except asyncio.TimeoutError:
            log.warning("HF scenario parse timed out — falling back to mock")
            return await self._mock.parse_scenario(text)
        except Exception as e:
            # Never expose token in logs
            log.warning("HF scenario parse failed (%s) — falling back to mock", type(e).__name__)
            return await self._mock.parse_scenario(text)

    async def analyze_safety(
        self,
        metrics: dict[str, Any],
        safety_state: dict[str, Any],
        sim_time_min: float,
        sim_status: str,
        emergency: dict | None = None,
        route_changes: list[dict] | None = None,
    ) -> SafetyAnalysis:
        client = _get_client()
        if client is None:
            return await self._mock.analyze_safety(
                metrics, safety_state, sim_time_min, sim_status, emergency, route_changes
            )

        # Build bottleneck detail string
        bottlenecks = safety_state.get("bottlenecks", [])
        bn_lines = []
        for bn in bottlenecks[:3]:
            ttc = bn.get("timeToCriticalMin")
            ttc_str = f", TTC: {ttc:.0f}min" if ttc else ""
            bn_lines.append(
                f"  - {bn.get('location')}: density={bn.get('currentDensity', 0):.0%}, "
                f"risk={bn.get('risk')}{ttc_str}"
            )

        em_status = "None"
        if emergency and emergency.get("active"):
            em_status = f"ACTIVE — {emergency.get('type')} at {emergency.get('location')}"

        rc_str = "None"
        if route_changes:
            rc_str = "; ".join(
                rc.get("reason", "") for rc in (route_changes or [])[:2]
            )

        ttc = safety_state.get("timeToCriticalMin")
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
            ttc=f"{ttc:.0f} min" if ttc else "N/A",
            bn_count=len(bottlenecks),
            bottleneck_details="\n".join(bn_lines) if bn_lines else "  None",
            emergency_status=em_status,
            route_changes=rc_str,
        )

        try:
            raw = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.chat_completion(
                        messages=[
                            {"role": "system", "content": SAFETY_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=768,
                        temperature=0.2,
                    ),
                ),
                timeout=settings.ai_timeout,
            )
            content = raw.choices[0].message.content
            data = _extract_json(content)
            if data is None:
                raise ValueError("Model returned non-JSON output")

            analysis = SafetyAnalysis(**{
                k: v for k, v in data.items() if k in SafetyAnalysis.model_fields
            })
            log.info(
                "HF safety analysis succeeded | urgency=%s risk=%s",
                analysis.urgency, safety_state.get("riskLevel"),
            )
            return analysis

        except asyncio.TimeoutError:
            log.warning("HF safety analysis timed out — using mock")
            return await self._mock.analyze_safety(
                metrics, safety_state, sim_time_min, sim_status, emergency, route_changes
            )
        except Exception as e:
            log.warning("HF safety analysis failed (%s) — using mock", type(e).__name__)
            return await self._mock.analyze_safety(
                metrics, safety_state, sim_time_min, sim_status, emergency, route_changes
            )
