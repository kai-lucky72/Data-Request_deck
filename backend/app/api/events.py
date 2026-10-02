"""Authenticated Server-Sent Events endpoint for live workspace refreshes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.models.user import User
from app.services.events import event_broker

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("")
async def stream_updates(
    _current_user: Annotated[User, Depends(get_current_user)],
):
    """Open a live refresh stream after normal bearer-token authentication."""
    queue = event_broker.subscribe()
    return StreamingResponse(
        event_broker.stream(queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
