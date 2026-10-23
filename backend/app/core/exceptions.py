from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class SimulationNotFoundError(Exception):
    def __init__(self, sim_id: str):
        super().__init__(f"Simulation '{sim_id}' not found")
        self.sim_id = sim_id


class SimulationStateError(Exception):
    """Raised when a lifecycle action is invalid for the current state."""


class VenueNotFoundError(Exception):
    def __init__(self, venue_id: str):
        super().__init__(f"Venue '{venue_id}' not found")
        self.venue_id = venue_id


class ScenarioValidationError(Exception):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class AIProviderError(Exception):
    """Raised when the AI provider fails; simulation must continue."""


class EmergencyNotFoundError(Exception):
    def __init__(self, em_id: str):
        super().__init__(f"Emergency '{em_id}' not found")


# ── FastAPI exception handlers ────────────────────────────────────────────────

async def simulation_not_found_handler(
    request: Request, exc: SimulationNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": "simulation_not_found", "message": str(exc)},
    )


async def simulation_state_handler(
    request: Request, exc: SimulationStateError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"error": "invalid_state", "message": str(exc)},
    )


async def venue_not_found_handler(
    request: Request, exc: VenueNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": "venue_not_found", "message": str(exc)},
    )


async def scenario_validation_handler(
    request: Request, exc: ScenarioValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": "scenario_validation_error",
            "message": str(exc),
            "details": exc.details,
        },
    )


def register_exception_handlers(app) -> None:  # type: ignore[no-untyped-def]
    app.add_exception_handler(SimulationNotFoundError, simulation_not_found_handler)
    app.add_exception_handler(SimulationStateError, simulation_state_handler)
    app.add_exception_handler(VenueNotFoundError, venue_not_found_handler)
    app.add_exception_handler(ScenarioValidationError, scenario_validation_handler)
