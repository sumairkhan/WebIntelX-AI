from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.database.models import User
from app.database.repositories import get_website_for_user
from app.graph.service import GraphService

router = APIRouter(prefix="/api", tags=["graph"])


@router.get("/websites/{website_id}/graph")
def get_graph_endpoint(
    website_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    website = get_website_for_user(db, user_id=current_user.id, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    return GraphService(db).build_graph(website_id, max_nodes=50)
