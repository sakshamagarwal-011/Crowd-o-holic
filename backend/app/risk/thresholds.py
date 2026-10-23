from __future__ import annotations

"""
Configuration-driven risk thresholds.
"""

from app.core.config import settings


class RiskThresholds:
    """Thresholds loaded from configuration — not hardcoded."""

    # Density thresholds for risk level
    density_moderate: float = settings.risk_density_moderate
    density_high: float = settings.risk_density_high
    density_critical: float = settings.risk_density_critical
    density_emergency: float = settings.risk_density_emergency

    # Utilization thresholds
    utilization_moderate: float = settings.risk_utilization_moderate
    utilization_high: float = settings.risk_utilization_high
    utilization_critical: float = settings.risk_utilization_critical

    # Bottleneck detection
    bottleneck_density: float = settings.bottleneck_density_threshold
    bottleneck_utilization: float = settings.bottleneck_utilization_threshold
    bottleneck_queue_growth: float = settings.bottleneck_queue_growth_threshold
    bottleneck_persistence: int = settings.bottleneck_persistence_ticks


THRESHOLDS = RiskThresholds()
