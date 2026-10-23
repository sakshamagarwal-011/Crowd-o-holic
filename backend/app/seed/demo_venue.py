from __future__ import annotations

"""
Demo venue seed data — Stadium A.
Node and edge IDs match the frontend's data/venue.ts exactly so that
snapshots are compatible with the existing UI without any changes.
"""

from app.graph.graph import VenueGraph
from app.graph.nodes import GraphNode
from app.graph.edges import GraphEdge


def _make_edge(
    eid: str, from_id: str, to_id: str, width: float, length: float, cost: float
) -> GraphEdge:
    """Capacity formula matches frontend: width * length * 0.6."""
    capacity = max(1, round(width * length * 0.6))
    return GraphEdge(
        id=eid,
        from_node=from_id,
        to_node=to_id,
        width=width,
        length=length,
        base_cost=cost,
        capacity=capacity,
    )


def build_stadium_a() -> VenueGraph:
    """Build the Stadium A venue graph — mirrors frontend venue.ts."""
    g = VenueGraph(
        venue_id="venue-stadium-a",
        name="Stadium A",
        width=1000.0,
        height=620.0,
    )

    # ── Nodes ─────────────────────────────────────────────────────────────────
    nodes = [
        # Entry gates
        GraphNode("gate-w",   "West Gate",           "entry",    60,  310, 1200, "Primary west entrance"),
        GraphNode("gate-e",   "East Gate",           "entry",   940,  310, 1800, "Primary east entrance — high volume"),
        GraphNode("gate-s",   "South Gate",          "entry",   500,  580,  800, "Secondary south entrance"),
        # Exit gates
        GraphNode("exit-n",   "North Exit",          "exit",    500,   45, 2000, "Emergency evacuation exit"),
        GraphNode("exit-sw",  "SW Exit",             "exit",    110,  540,  900, "South-west evacuation exit"),
        GraphNode("exit-se",  "SE Exit",             "exit",    890,  540,  900, "South-east evacuation exit"),
        # Junctions
        GraphNode("j-w",      "West Junction",       "junction", 220, 310, 1500),
        GraphNode("j-e",      "East Junction",       "junction", 780, 310, 1500),
        GraphNode("j-n",      "North Junction",      "junction", 500, 180, 1800),
        GraphNode("j-s",      "South Junction",      "junction", 500, 440, 1600),
        GraphNode("j-nw",     "NW Corridor",         "junction", 330, 210, 1000, "North-west corridor junction"),
        GraphNode("j-ne",     "NE Corridor",         "junction", 670, 210, 1000, "North-east corridor junction"),
        GraphNode("j-sw",     "SW Corridor",         "junction", 330, 420, 1000, "South-west corridor junction"),
        GraphNode("j-se",     "SE Corridor",         "junction", 670, 420, 1000, "South-east corridor junction"),
        # Facilities
        GraphNode("food-n",   "North Food Court",    "food",    420, 110,  600, "Food stalls — north corridor"),
        GraphNode("food-s",   "South Food Court",    "food",    580, 510,  600, "Food stalls — south plaza"),
        GraphNode("medical",  "Medical Station",     "medical", 500, 310,  200, "First-aid & medical"),
        # Stage
        GraphNode("stage",    "Main Stage",          "stage",   500, 260, 12000, "Concert main stage"),
    ]
    for n in nodes:
        g.add_node(n)

    # ── Edges ─────────────────────────────────────────────────────────────────
    # Entries → junctions
    edges = [
        _make_edge("e-gw-jw",   "gate-w", "j-w",    6, 160, 1.0),
        _make_edge("e-ge-je",   "gate-e", "j-e",    7, 160, 1.0),
        _make_edge("e-gs-js",   "gate-s", "j-s",    5, 140, 1.2),

        # Junction ring
        _make_edge("e-jw-jnw",  "j-w",   "j-nw",   4, 130, 1.1),
        _make_edge("e-jw-jsw",  "j-w",   "j-sw",   4, 130, 1.1),
        _make_edge("e-je-jne",  "j-e",   "j-ne",   4, 130, 1.1),
        _make_edge("e-je-jse",  "j-e",   "j-se",   4, 130, 1.1),
        _make_edge("e-jnw-jn",  "j-nw",  "j-n",    5, 180, 1.0),
        _make_edge("e-jne-jn",  "j-ne",  "j-n",    5, 180, 1.0),
        _make_edge("e-jsw-js",  "j-sw",  "j-s",    5, 180, 1.0),
        _make_edge("e-jse-js",  "j-se",  "j-s",    5, 180, 1.0),

        # North corridor (bottleneck-prone)
        _make_edge("e-jn-foodn",    "j-n",    "food-n",  3,  90, 1.3),
        _make_edge("e-foodn-exitn", "food-n", "exit-n",  4,  80, 1.0),

        # Central connections to stage
        _make_edge("e-jn-stage",  "j-n", "stage",   6,  90, 0.8),
        _make_edge("e-js-stage",  "j-s", "stage",   6,  90, 0.8),
        _make_edge("e-jw-stage",  "j-w", "stage",   4, 180, 1.2),
        _make_edge("e-je-stage",  "j-e", "stage",   4, 180, 1.2),

        # Medical
        _make_edge("e-stage-medical", "stage", "medical", 3, 60, 1.5),

        # South food
        _make_edge("e-js-foods",  "j-s", "food-s",  3,  90, 1.3),

        # Exits
        _make_edge("e-jsw-exitsw",   "j-sw",   "exit-sw", 4, 160, 1.0),
        _make_edge("e-jse-exitse",   "j-se",   "exit-se", 4, 160, 1.0),
        _make_edge("e-foods-exitsw", "food-s", "exit-sw", 3, 200, 1.2),
        _make_edge("e-foods-exitse", "food-s", "exit-se", 3, 200, 1.2),
    ]
    for e in edges:
        g.add_edge(e, bidirectional=True)

    return g


# Singleton instance — loaded once at startup
STADIUM_A: VenueGraph = build_stadium_a()

# All venues by id
VENUE_REGISTRY: dict[str, VenueGraph] = {
    STADIUM_A.venue_id: STADIUM_A,
}
