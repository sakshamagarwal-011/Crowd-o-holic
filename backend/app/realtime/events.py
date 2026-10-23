from __future__ import annotations

"""
Event type constants and payload schemas for WebSocket communication.
Every event has a predictable schema.
"""

from typing import Any, Literal

EventType = Literal[
    "simulation.started",
    "simulation.paused",
    "simulation.updated",
    "simulation.completed",
    "metrics.updated",
    "risk.updated",
    "bottleneck.detected",
    "bottleneck.cleared",
    "route.changed",
    "emergency.started",
    "emergency.updated",
    "emergency.resolved",
    "ai.analysis.updated",
    "connection.status",
    "error",
]


def make_event(event_type: EventType, payload: Any) -> dict:
    """Construct a WebSocket event message."""
    return {"type": event_type, "payload": payload}


def make_connection_event(status: str, message: str = "") -> dict:
    return make_event("connection.status", {"status": status, "message": message})


def make_error_event(code: str, message: str) -> dict:
    return make_event("error", {"code": code, "message": message})
