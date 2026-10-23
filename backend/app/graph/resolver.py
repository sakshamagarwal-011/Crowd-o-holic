from __future__ import annotations

"""
Venue Graph Location Resolver.
Resolves natural-language descriptions (e.g. 'front stage', 'medical access corridor',
'main entrance') to validated VenueGraph nodes and edges.
Preserves original descriptions and flags unresolved locations without inventing IDs.
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.graph.graph import VenueGraph


@dataclass
class LocationResolutionResult:
    original_text: str
    resolved_node_id: str | None = None
    resolved_edge_id: str | None = None
    is_resolved: bool = False
    matched_entity_type: str | None = None  # "node" | "edge"
    display_label: str = ""
    confidence: float = 0.0
    warning: str | None = None

    def to_dict(self) -> dict:
        return {
            "original_text": self.original_text,
            "resolved_node_id": self.resolved_node_id,
            "resolved_edge_id": self.resolved_edge_id,
            "is_resolved": self.is_resolved,
            "matched_entity_type": self.matched_entity_type,
            "display_label": self.display_label,
            "confidence": round(self.confidence, 2),
            "warning": self.warning,
        }


# Curated venue alias map (normalized lower-case regex or phrases to graph elements)
_EDGE_ALIASES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(?:medical\s+access\s+corridor|medical\s+corridor|corridor\s+to\s+medical|path\s+to\s+medical|stage[- ]to[- ]medical)\b", re.I), "e-stage-medical", "Medical Access Corridor"),
    (re.compile(r"\b(?:main\s+entrance\s+corridor|east\s+gate\s+corridor|east\s+entrance\s+corridor|main\s+entry\s+corridor)\b", re.I), "e-ge-je", "Main Entrance Corridor"),
    (re.compile(r"\b(?:west\s+gate\s+corridor|west\s+entrance\s+corridor)\b", re.I), "e-gw-jw", "West Entrance Corridor"),
    (re.compile(r"\b(?:south\s+gate\s+corridor|south\s+entrance\s+corridor)\b", re.I), "e-gs-js", "South Entrance Corridor"),
    (re.compile(r"\b(?:north\s+corridor|corridor\s+to\s+north\s+food)\b", re.I), "e-jn-foodn", "North Corridor"),
    (re.compile(r"\b(?:central\s+corridor|center\s+corridor|central\s+junction\s+corridor)\b", re.I), "e-jn-stage", "Central Corridor"),
    (re.compile(r"\b(?:stage\s+corridor|corridor\s+near\s+(?:the\s+)?(?:main\s+)?stage|corridor\s+to\s+(?:the\s+)?(?:main\s+)?stage|nearest\s+corridor(?:\s+to\s+stage)?)\b", re.I), "e-jn-stage", "Stage Corridor (Central)"),
    (re.compile(r"\b(?:south\s+stage\s+corridor|corridor\s+south\s+of\s+stage)\b", re.I), "e-js-stage", "South Stage Corridor"),
]

_NODE_ALIASES: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(?:front[- ]stage(?:\s+area)?|front\s+stage|main\s+stage|stage\s+area|stage|stage['’]s?\s+electrical(?:\s+equipment)?|suspected\s+fire\s+location)\b", re.I), "stage", "Main Stage"),
    (re.compile(r"\b(?:central\s+junction|center\s+junction|middle\s+junction|central\s+hub|central\s+plaza|central\s+area|center\s+area)\b", re.I), "stage", "Central Hub (Main Stage)"),
    (re.compile(r"\b(?:medical\s+station|medical\s+tent|first[- ]aid(?:\s+station)?|first\s+aid|infirmary)\b", re.I), "medical", "Medical Station"),
    (re.compile(r"\b(?:main\s+entrance|main\s+gate|east\s+gate|primary\s+east\s+entrance|east\s+entrance)\b", re.I), "gate-e", "East Gate (Main Entrance)"),
    (re.compile(r"\b(?:west\s+gate|primary\s+west\s+entrance|west\s+entrance)\b", re.I), "gate-w", "West Gate"),
    (re.compile(r"\b(?:south\s+gate|secondary\s+south\s+entrance|south\s+entrance)\b", re.I), "gate-s", "South Gate"),
    (re.compile(r"\b(?:north\s+exit|emergency\s+exit|evacuation\s+exit|two\s+alternative\s+exits|alternative\s+exits?)\b", re.I), "exit-n", "North Exit"),
    (re.compile(r"\b(?:south[- ]west\s+exit|sw\s+exit)\b", re.I), "exit-sw", "SW Exit"),
    (re.compile(r"\b(?:south[- ]east\s+exit|se\s+exit)\b", re.I), "exit-se", "SE Exit"),
    (re.compile(r"\b(?:north\s+food(?:\s+court)?|food[- ]n)\b", re.I), "food-n", "North Food Court"),
    (re.compile(r"\b(?:south\s+food(?:\s+court)?|food[- ]s)\b", re.I), "food-s", "South Food Court"),
    (re.compile(r"\b(?:west\s+junction|j[- ]w)\b", re.I), "j-w", "West Junction"),
    (re.compile(r"\b(?:east\s+junction|j[- ]e)\b", re.I), "j-e", "East Junction"),
    (re.compile(r"\b(?:north\s+junction|j[- ]n)\b", re.I), "j-n", "North Junction"),
    (re.compile(r"\b(?:south\s+junction|j[- ]s)\b", re.I), "j-s", "South Junction"),
    (re.compile(r"\b(?:nw\s+corridor|north[- ]west\s+corridor(?:\s+junction)?|j[- ]nw)\b", re.I), "j-nw", "NW Corridor"),
    (re.compile(r"\b(?:ne\s+corridor|north[- ]east\s+corridor(?:\s+junction)?|j[- ]ne)\b", re.I), "j-ne", "NE Corridor"),
    (re.compile(r"\b(?:sw\s+corridor|south[- ]west\s+corridor(?:\s+junction)?|j[- ]sw)\b", re.I), "j-sw", "SW Corridor"),
    (re.compile(r"\b(?:se\s+corridor|south[- ]east\s+corridor(?:\s+junction)?|j[- ]se)\b", re.I), "j-se", "SE Corridor"),
]


def resolve_location(
    location_text: str,
    graph: VenueGraph,
) -> LocationResolutionResult:
    """
    Resolve a free-text location to a verified node or edge in the VenueGraph.
    Returns LocationResolutionResult with is_resolved=False if no mapping exists.
    """
    clean = location_text.strip()
    if not clean:
        return LocationResolutionResult(
            original_text=location_text,
            is_resolved=False,
            warning="Empty location string provided",
        )

    # 1. Direct Node ID match
    node = graph.get_node(clean)
    if node:
        return LocationResolutionResult(
            original_text=location_text,
            resolved_node_id=node.id,
            is_resolved=True,
            matched_entity_type="node",
            display_label=node.label,
            confidence=1.0,
        )

    # 2. Direct Edge ID match
    edge = graph.get_edge(clean)
    if edge:
        from_node = graph.get_node(edge.from_node)
        to_node = graph.get_node(edge.to_node)
        label = f"{from_node.label if from_node else edge.from_node} ↔ {to_node.label if to_node else edge.to_node}"
        return LocationResolutionResult(
            original_text=location_text,
            resolved_edge_id=edge.id,
            is_resolved=True,
            matched_entity_type="edge",
            display_label=label,
            confidence=1.0,
        )

    # 3. Check Edge aliases (corridors)
    for pattern, eid, label in _EDGE_ALIASES:
        if pattern.search(clean):
            if eid in graph.edges:
                return LocationResolutionResult(
                    original_text=location_text,
                    resolved_edge_id=eid,
                    is_resolved=True,
                    matched_entity_type="edge",
                    display_label=label,
                    confidence=0.95,
                )

    # 4. Check Node aliases
    for pattern, nid, label in _NODE_ALIASES:
        if pattern.search(clean):
            if nid in graph.nodes:
                return LocationResolutionResult(
                    original_text=location_text,
                    resolved_node_id=nid,
                    is_resolved=True,
                    matched_entity_type="node",
                    display_label=label,
                    confidence=0.95,
                )

    # 5. Token / word boundary match against graph nodes
    lower_clean = clean.lower()
    for nid, node in graph.nodes.items():
        node_label_lower = node.label.lower()
        if lower_clean == node_label_lower:
            return LocationResolutionResult(
                original_text=location_text,
                resolved_node_id=nid,
                is_resolved=True,
                matched_entity_type="node",
                display_label=node.label,
                confidence=0.9,
            )
        # Require word boundary matching if clean text is part of node label (avoid matching 'in' -> 'Main Stage')
        if len(lower_clean) >= 3 and re.search(rf"\b{re.escape(lower_clean)}\b", node_label_lower):
            return LocationResolutionResult(
                original_text=location_text,
                resolved_node_id=nid,
                is_resolved=True,
                matched_entity_type="node",
                display_label=node.label,
                confidence=0.85,
            )
        # Require word boundary matching if node label is part of clean text
        if len(node_label_lower) >= 3 and re.search(rf"\b{re.escape(node_label_lower)}\b", lower_clean):
            return LocationResolutionResult(
                original_text=location_text,
                resolved_node_id=nid,
                is_resolved=True,
                matched_entity_type="node",
                display_label=node.label,
                confidence=0.80,
            )

    # 6. Unresolved location: preserve original text and flag warning
    return LocationResolutionResult(
        original_text=location_text,
        is_resolved=False,
        confidence=0.0,
        warning=f"Location '{location_text}' could not be resolved to any verified venue node or corridor.",
    )
