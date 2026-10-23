from __future__ import annotations

"""
Venue service — loads and provides venue graphs.
"""

import copy
from app.graph.graph import VenueGraph
from app.seed.demo_venue import VENUE_REGISTRY
from app.core.exceptions import VenueNotFoundError


def get_venue(venue_id: str) -> VenueGraph:
    """Get a venue graph by ID."""
    venue = VENUE_REGISTRY.get(venue_id)
    if venue is None:
        raise VenueNotFoundError(venue_id)
    return venue


def get_venue_for_simulation(venue_id: str) -> VenueGraph:
    """
    Get a fresh copy of the venue graph for a simulation.
    Each simulation gets its own graph instance so state is isolated.
    """
    template = get_venue(venue_id)
    # Deep copy to isolate runtime state per simulation
    import copy as cp
    fresh = VenueGraph(
        venue_id=template.venue_id,
        name=template.name,
        width=template.width,
        height=template.height,
    )
    for node in template.nodes.values():
        import dataclasses
        fresh.add_node(dataclasses.replace(node))
    for edge in template.edges.values():
        fresh.add_edge(dataclasses.replace(edge), bidirectional=True)
    return fresh


def list_venues() -> list[dict]:
    return [v.to_frontend_dict() for v in VENUE_REGISTRY.values()]
