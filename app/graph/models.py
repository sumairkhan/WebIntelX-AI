from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    type: str
    label: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    relationship_type: str
    strength: float = 0.0
    metadata: dict[str, object] = field(default_factory=dict)
