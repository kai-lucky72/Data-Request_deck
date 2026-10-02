"""Authenticated Server-Sent Events endpoint for live workspace refreshes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.services.events import event_broker

router = APIRouter(prefix="/events", tags=["Events"])


def get_stream_user(authorization: str | None = Header(default=None)) -> bool:
    """Authenticate a stream without holding a database session open for its life."""
    scheme, _, token = (authorization or "").partition(" ")
    payload = decode_access_token(token) if scheme.lower() == "bearer" and token else None
    try:
        user_id = int(payload.get("sub")) if payload else None
    except (TypeError, ValueError):
        user_id = None
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate stream credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate stream credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return True


@router.get("")
async def stream_updates(
    _authenticated: Annotated[bool, Depends(get_stream_user)],
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
