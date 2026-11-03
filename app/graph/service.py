from __future__ import annotations

from sqlalchemy.orm import Session

from app.graph.builder import GraphBuilder


class GraphService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build_graph(self, website_id: int, *, max_nodes: int = 50) -> dict[str, object]:
        return GraphBuilder.build(website_id, session=self.session, max_nodes=max_nodes)
