from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas
import asyncio
import json
from typing import Optional

router = APIRouter(prefix="/items", tags=["items"])

def _sse(event: Optional[str] = None, data: Optional[dict | str] = None, retry_ms: Optional[int] = None) -> str:
    lines: list[str] = []
    if event:
        lines.append(f"event: {event}")
    if retry_ms is not None:
        lines.append(f"retry: {retry_ms}")
    if data is not None:
        payload = json.dumps(data, separators=(",", ":")) if isinstance(data, (dict, list)) else str(data)
        for ln in payload.splitlines() or [""]:
            lines.append(f"data: {ln}")
    lines.append("")  # blank line to terminate event
    return "\n".join(lines)

async def _progress_stream(request: Request, steps: int, delay: float):
    yield _sse(event="hello", data={"msg": "stream-start"}, retry_ms=1500)
    for i in range(steps + 1):
        if await request.is_disconnected():
            break
        pct = int((i / steps) * 100)
        yield _sse(event="progress", data={"progress": pct})
        await asyncio.sleep(delay)
    if not await request.is_disconnected():
        yield _sse(event="done", data={"status": "ok"})

@router.get("/_stream", summary="SSE: progress demo using async generator")
async def stream_progress(
    request: Request,
    steps: int = Query(20, ge=1, le=10_000),
    delay: float = Query(0.25, gt=0, le=60),
):
    """
    Server-Sent Events endpoint.

    Usage:
      GET /items/_stream?steps=25&delay=0.2

    Notes:
      - Content-Type: text/event-stream
      - Each event is JSON in `data:` lines and ends with a blank line.
      - Client can use EventSource in the browser or `curl -N`.
    """
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Transfer-Encoding": "chunked",
        "Access-Control-Allow-Origin": "*",
    }
    return StreamingResponse(_progress_stream(request, steps=steps, delay=delay), headers=headers)

async def _items_ping_stream(request: Request, db: Session, interval: float):
    yield _sse(event="hello", data={"msg": "items-ping-start"})
    while not await request.is_disconnected():
        try:
            # NOTE: simple/portable way without adding new CRUD methods.
            count = len(crud.list_items(db, 0, 1_000_000))
        except Exception:
            count = None
        yield _sse(event="ping", data={"ts": asyncio.get_running_loop().time(), "itemsCount": count})
        await asyncio.sleep(interval)

@router.get("/stream-ping", summary="SSE: heartbeat + items count (polling DB)")
async def stream_ping(request: Request, db: Session = Depends(get_db), interval: float = Query(2.0, gt=0, le=60)):
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
    }
    return StreamingResponse(_items_ping_stream(request, db, interval), headers=headers)

# -----------------------
# CRUD endpoints
# -----------------------

@router.post("/", response_model=schemas.ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: schemas.ItemCreate, db: Session = Depends(get_db)):
    return crud.create_item(db, payload)

@router.get("/", response_model=list[schemas.ItemOut])
def list_items(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return crud.list_items(db, skip=skip, limit=limit)

@router.get("/{item_id}", response_model=schemas.ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    obj = crud.get_item(db, item_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Item not found")
