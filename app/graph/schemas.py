from __future__ import annotations

from pydantic import BaseModel


class GraphResponse(BaseModel):
    nodes: list[dict[str, object]]
    edges: list[dict[str, object]]
    summary: dict[str, object]
