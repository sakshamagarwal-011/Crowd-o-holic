from __future__ import annotations

"""
Abstract AIProvider interface.
The simulation engine depends on this abstraction, not on HuggingFace directly.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.ai.schemas import ScenarioParseResult, SafetyAnalysis


class AIProvider(ABC):
    """Abstract base for all AI providers."""

    @abstractmethod
    async def parse_scenario(self, text: str) -> ScenarioParseResult:
        """
        Parse a natural language scenario description into structured parameters.
        Must NOT block the simulation or raise unhandled exceptions.
        """
        ...

    @abstractmethod
    async def analyze_safety(
        self,
        metrics: dict[str, Any],
        safety_state: dict[str, Any],
        sim_time_min: float,
        sim_status: str,
        emergency: dict | None = None,
        route_changes: list[dict] | None = None,
    ) -> SafetyAnalysis:
        """
        Generate a safety analysis based on current simulation state.
        Must NOT recalculate risk scores, routes, or density.
        Must NOT block the simulation or raise unhandled exceptions.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        ...
