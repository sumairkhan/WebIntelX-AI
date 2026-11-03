from __future__ import annotations

from typing import Any

from app.database.models import Correlation, Event, Finding


class GraphBuilder:
    @staticmethod
    def build(website_id: int, *, session: Any, max_nodes: int = 50) -> dict[str, Any]:
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []
        seen_nodes: set[tuple[str, str]] = set()
        seen_edges: set[tuple[str, str, str]] = set()

        events = session.query(Event).filter(Event.website_id == website_id).order_by(Event.timestamp.asc()).limit(max_nodes).all()
        for event in events:
            key = ("event", f"event-{event.id}")
            if key not in seen_nodes:
                nodes.append({"id": f"event-{event.id}", "type": "event", "label": event.event_type, "metadata": {"event_id": event.id}})
                seen_nodes.add(key)

            for finding in event.findings:
                k = ("finding", f"finding-{finding.id}")
                if k not in seen_nodes:
                    nodes.append({"id": f"finding-{finding.id}", "type": "finding", "label": finding.finding_type, "metadata": {"finding_id": finding.id}})
                    seen_nodes.add(k)
                edge_key = (f"event-{event.id}", f"finding-{finding.id}", "event_to_finding")
                if edge_key not in seen_edges:
                    edges.append({"source": f"event-{event.id}", "target": f"finding-{finding.id}", "relationship_type": "event_to_finding", "strength": float(finding.confidence)})
                    seen_edges.add(edge_key)

        correlations = session.query(Correlation).filter(Correlation.event_id.in_([event.id for event in events]), Correlation.related_event_id.in_([event.id for event in events])).all()
        for correlation in correlations:
            key = ("correlation", f"correlation-{correlation.id}")
            if key not in seen_nodes:
                nodes.append({"id": f"correlation-{correlation.id}", "type": "correlation", "label": correlation.relationship_type, "metadata": {"strength": correlation.strength}})
                seen_nodes.add(key)

            for node_id, source_type in [
                (f"event-{correlation.event_id}", "event"),
                (f"event-{correlation.related_event_id}", "event"),
            ]:
                edge_key = (node_id, f"correlation-{correlation.id}", "event_to_correlation")
                if edge_key not in seen_edges:
                    edges.append({"source": node_id, "target": f"correlation-{correlation.id}", "relationship_type": "event_to_correlation", "strength": float(correlation.strength)})
                    seen_edges.add(edge_key)

        return {"nodes": nodes[:max_nodes], "edges": edges[:max_nodes], "summary": {"node_count": len(nodes), "edge_count": len(edges)}}
