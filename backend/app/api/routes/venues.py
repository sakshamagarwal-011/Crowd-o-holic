from __future__ import annotations

from fastapi import APIRouter
from app.services.venue_service import get_venue, list_venues
from app.core.exceptions import VenueNotFoundError

router = APIRouter(prefix="/api/venues", tags=["Venues"])


@router.get("")
async def list_all_venues():
    return list_venues()


@router.get("/{venue_id}")
async def get_venue_by_id(venue_id: str):
    graph = get_venue(venue_id)
    return graph.to_frontend_dict()
