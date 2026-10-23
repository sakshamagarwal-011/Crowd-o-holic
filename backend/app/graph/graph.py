from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Callable

from app.graph.nodes import GraphNode
from app.graph.edges import GraphEdge


@dataclass
class VenueGraph:
    """
    Graph representation of a venue.
    Supports A* pathfinding with dynamic congestion-aware edge costs.
    Edges are bidirectional (unless forced directional by configuration).
    """
    venue_id: str
    name: str
    width: float
    height: float

    _nodes: dict[str, GraphNode] = field(default_factory=dict)
    _edges: dict[str, GraphEdge] = field(default_factory=dict)
    # adjacency: node_id → list of (neighbor_id, edge_id)
    _adj: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    # ── Graph construction ────────────────────────────────────────────────────

    def add_node(self, node: GraphNode) -> None:
        self._nodes[node.id] = node
        if node.id not in self._adj:
            self._adj[node.id] = []

    def add_edge(self, edge: GraphEdge, bidirectional: bool = True) -> None:
        self._edges[edge.id] = edge
        # from → to
        self._adj.setdefault(edge.from_node, []).append((edge.to_node, edge.id))
        if bidirectional:
            # to → from (same edge id, reversed direction)
            self._adj.setdefault(edge.to_node, []).append((edge.from_node, edge.id))

    # ── Accessors ─────────────────────────────────────────────────────────────

    @property
    def nodes(self) -> dict[str, GraphNode]:
        return self._nodes

    @property
    def edges(self) -> dict[str, GraphEdge]:
        return self._edges

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> GraphEdge | None:
        return self._edges.get(edge_id)

    def get_edge_between(self, a: str, b: str) -> GraphEdge | None:
        """Return the edge (any direction) between nodes a and b."""
        for neighbor, edge_id in self._adj.get(a, []):
            if neighbor == b:
                return self._edges.get(edge_id)
        return None

    def neighbors(self, node_id: str, traversable_only: bool = True) -> list[tuple[str, str]]:
        """Returns (neighbor_id, edge_id) pairs."""
        result = []
        for neighbor, edge_id in self._adj.get(node_id, []):
            edge = self._edges.get(edge_id)
            if edge is None:
                continue
            if traversable_only and not edge.is_traversable:
                continue
            result.append((neighbor, edge_id))
        return result

    def edges_from_node(self, node_id: str) -> list[GraphEdge]:
        """All edges connected to node_id."""
        seen: set[str] = set()
        result = []
        for _, edge_id in self._adj.get(node_id, []):
            if edge_id not in seen:
                seen.add(edge_id)
                e = self._edges.get(edge_id)
                if e:
                    result.append(e)
        return result

    # ── Pathfinding ───────────────────────────────────────────────────────────

    def _heuristic(self, a: str, b: str) -> float:
        """Euclidean distance heuristic for A*."""
        na = self._nodes.get(a)
        nb = self._nodes.get(b)
        if na is None or nb is None:
            return 0.0
        return math.hypot(na.x - nb.x, na.y - nb.y) / 100.0

    def find_path(
        self,
        source: str,
        destination: str,
        cost_fn: Callable[[GraphEdge], float] | None = None,
        excluded_edges: set[str] | None = None,
    ) -> list[str] | None:
        """
        A* pathfinding. Returns ordered list of node IDs or None if no path.
        cost_fn: optional override for edge cost (default: edge.dynamic_cost)
        excluded_edges: set of edge IDs to treat as impassable
        """
        if source == destination:
            return [source]
        if source not in self._nodes or destination not in self._nodes:
            return None

        excluded_edges = excluded_edges or set()

        def edge_cost(edge: GraphEdge) -> float:
            if edge.id in excluded_edges:
                return float("inf")
            if cost_fn is not None:
                return cost_fn(edge)
            return edge.dynamic_cost

        # Priority queue: (f_score, node_id)
        open_heap: list[tuple[float, str]] = []
        heapq.heappush(open_heap, (0.0, source))

        g_score: dict[str, float] = {source: 0.0}
        came_from: dict[str, str] = {}

        while open_heap:
            _, current = heapq.heappop(open_heap)

            if current == destination:
                return self._reconstruct_path(came_from, current)

            for neighbor, edge_id in self._adj.get(current, []):
                edge = self._edges.get(edge_id)
                if edge is None:
                    continue
                if not edge.is_traversable:
                    continue
                c = edge_cost(edge)
                if c == float("inf"):
                    continue

                tentative_g = g_score.get(current, float("inf")) + c
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + self._heuristic(neighbor, destination)
                    heapq.heappush(open_heap, (f, neighbor))

        return None  # no path found

    def _reconstruct_path(self, came_from: dict[str, str], current: str) -> list[str]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def find_path_edges(
        self,
        source: str,
        destination: str,
        cost_fn: Callable[[GraphEdge], float] | None = None,
        excluded_edges: set[str] | None = None,
    ) -> list[GraphEdge] | None:
        """Returns ordered list of GraphEdge objects for the path."""
        path = self.find_path(source, destination, cost_fn, excluded_edges)
        if path is None or len(path) < 2:
            return None
        edges = []
        for i in range(len(path) - 1):
            e = self.get_edge_between(path[i], path[i + 1])
            if e is None:
                return None
            edges.append(e)
        return edges

    # ── State management ──────────────────────────────────────────────────────

    def close_edge(self, edge_id: str) -> None:
        e = self._edges.get(edge_id)
        if e:
            e.disabled = True
            e.status = "emergency-closed"

    def open_edge(self, edge_id: str) -> None:
        e = self._edges.get(edge_id)
        if e:
            e.disabled = False
            e.status = "open"

    def close_node_edges(self, node_id: str) -> list[str]:
        """Close all edges connected to node_id. Returns list of closed edge IDs."""
        closed = []
        seen: set[str] = set()
        for _, edge_id in self._adj.get(node_id, []):
            if edge_id not in seen:
                seen.add(edge_id)
                self.close_edge(edge_id)
                closed.append(edge_id)
        return closed

    def reset_edge_flows(self) -> None:
        """Zero out runtime state — called on simulation reset."""
        for edge in self._edges.values():
            edge.flow = 0.0
            edge.density = 0.0
            edge.current_occupancy = 0
            if not edge.disabled:
                edge.status = "open"

    def reset_node_occupancy(self) -> None:
        for node in self._nodes.values():
            node.current_occupancy = 0

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_frontend_dict(self) -> dict:
        return {
            "id": self.venue_id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "nodes": [n.to_frontend_dict() for n in self._nodes.values()],
            "edges": [e.to_frontend_dict() for e in self._edges.values()],
        }
