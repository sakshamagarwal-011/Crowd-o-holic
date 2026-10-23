"""
Tests for the venue graph — nodes, edges, A* pathfinding, closures.
"""
import pytest
from app.graph.nodes import GraphNode
from app.graph.edges import GraphEdge
from app.graph.graph import VenueGraph


def make_simple_graph() -> VenueGraph:
    g = VenueGraph(venue_id="test", name="Test", width=100, height=100)
    g.add_node(GraphNode("a", "A", "entry",   0, 50, 100))
    g.add_node(GraphNode("b", "B", "junction", 50, 50, 200))
    g.add_node(GraphNode("c", "C", "exit",    100, 50, 100))
    g.add_node(GraphNode("d", "D", "junction", 50, 0,  150))
    # a-b, b-c (direct path), a-d, d-c (alternative)
    g.add_edge(GraphEdge("e-ab", "a", "b", 4, 50, 1.0, 120), bidirectional=True)
    g.add_edge(GraphEdge("e-bc", "b", "c", 4, 50, 1.0, 120), bidirectional=True)
    g.add_edge(GraphEdge("e-ad", "a", "d", 3, 80, 1.5, 100), bidirectional=True)
    g.add_edge(GraphEdge("e-dc", "d", "c", 3, 80, 1.5, 100), bidirectional=True)
    return g


def test_node_creation():
    g = make_simple_graph()
    assert g.get_node("a") is not None
    assert g.get_node("z") is None


def test_edge_creation():
    g = make_simple_graph()
    assert g.get_edge("e-ab") is not None
    assert len(g.edges) == 4


def test_edge_between():
    g = make_simple_graph()
    e = g.get_edge_between("a", "b")
    assert e is not None
    assert e.id == "e-ab"
    # Bidirectional
    e2 = g.get_edge_between("b", "a")
    assert e2 is not None


def test_pathfinding_direct():
    g = make_simple_graph()
    path = g.find_path("a", "c")
    assert path is not None
    assert path[0] == "a"
    assert path[-1] == "c"
    assert len(path) in (3, 4)  # either a-b-c or a-d-c


def test_pathfinding_same_node():
    g = make_simple_graph()
    path = g.find_path("a", "a")
    assert path == ["a"]


def test_pathfinding_no_path():
    g = make_simple_graph()
    g.add_node(GraphNode("isolated", "Isolated", "junction", 200, 200, 100))
    path = g.find_path("a", "isolated")
    assert path is None


def test_node_capacity():
    node = GraphNode("x", "X", "junction", 0, 0, 100)
    node.current_occupancy = 50
    assert abs(node.utilization - 0.5) < 0.01
    node.current_occupancy = 150
    assert node.utilization == 1.0


def test_edge_dynamic_cost():
    edge = GraphEdge("e", "a", "b", 4, 100, 1.0, 200)
    base_cost = edge.dynamic_cost
    edge.density = 0.8
    high_cost = edge.dynamic_cost
    assert high_cost > base_cost


def test_emergency_close_reopen():
    g = make_simple_graph()
    g.close_edge("e-ab")
    e = g.get_edge("e-ab")
    assert e.disabled
    assert e.status == "emergency-closed"
    # Path should go via d now
    path = g.find_path("a", "c")
    assert path is not None
    assert "b" not in path or all(seg != "e-ab" for seg in path)

    g.open_edge("e-ab")
    assert not e.disabled


def test_close_node_edges():
    g = make_simple_graph()
    closed = g.close_node_edges("b")
    assert len(closed) == 2   # e-ab and e-bc
    for eid in closed:
        assert g.get_edge(eid).disabled


def test_capacities_non_negative():
    g = make_simple_graph()
    for edge in g.edges.values():
        assert edge.capacity >= 0


def test_stadium_a_loads():
    from app.seed.demo_venue import STADIUM_A
    assert STADIUM_A.venue_id == "venue-stadium-a"
    assert len(STADIUM_A.nodes) == 18
    assert len(STADIUM_A.edges) > 15
    # Required nodes exist
    for nid in ["gate-e", "gate-w", "gate-s", "exit-n", "stage", "food-n"]:
        assert STADIUM_A.get_node(nid) is not None


def test_stadium_a_pathfinding():
    from app.seed.demo_venue import STADIUM_A
    from app.services.venue_service import get_venue_for_simulation
    g = get_venue_for_simulation("venue-stadium-a")
    # Key routes should be findable
    for src, dst in [("gate-e", "stage"), ("gate-w", "stage"), ("stage", "exit-n")]:
        path = g.find_path(src, dst)
        assert path is not None, f"No path from {src} to {dst}"
        assert path[0] == src
        assert path[-1] == dst
