from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["sdk"])
SDK_FILE = Path(__file__).resolve().parents[2] / "sdk" / "src" / "webintelx.js"


@router.get("/sdk/webintelx.js", include_in_schema=False)
def get_webintelx_sdk() -> FileResponse:
    if not SDK_FILE.is_file():
        raise HTTPException(status_code=404, detail="WebIntelX SDK is unavailable.")
    return FileResponse(SDK_FILE, media_type="application/javascript", filename="webintelx.js")
