"""Request lifecycle endpoints with role checks and ownership filtering."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.request import Request, RequestStatus, RequestStatusHistory
from app.schemas.request import RequestCreate, RequestResponse, RequestUpdateStatus
from app.services.status import change_request_status

router = APIRouter(
    prefix="/requests",
    tags=["Requests"]
)

@router.post("", response_model=RequestResponse,status_code=status.HTTP_201_CREATED)
def create_request(
    payload: RequestCreate,  # Validated body containing task, quantity, deadline, and notes.
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(UserRole.client, UserRole.admin))],
):
    """Create a submitted request owned by the authenticated client (or admin)."""
    # Owner comes from the authenticated identity, never from a user-supplied body field.
    request = Request(
        client_id=current_user.id,
        task_name=payload.task_name,
        episodes_requested=payload.episodes_requested,
        deadline=payload.deadline,
        notes=payload.notes,
        status=RequestStatus.submitted,
    )
    
    db.add(request)  # Stage the new object in this session; it is not committed yet.
    db.flush()  # Send INSERT now so the database generates request.id without committing.
    # Store the initial state as a history event so later duration analytics have
    # a real submitted timestamp rather than inferring it from a different field.
    db.add(RequestStatusHistory(
        request_id=request.id,
        from_status=None,
        to_status=RequestStatus.submitted,
        changed_by_id=current_user.id,
        changed_at=datetime.now(timezone.utc),
        note="Request created",
    ))
    db.commit()  # Request and initial history entry succeed or fail together.
    db.refresh(request)
    
    return request

@router.get("", response_model=list[RequestResponse])
def list_requests(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Clients see their own records; operations roles see the full work queue."""
    query = db.query(Request)  # Start with the database query before applying role scope.
    
    if current_user.role == UserRole.client:
        # Row-level authorization is enforced in SQL so other clients' data is never returned.
        query = query.filter(Request.client_id == current_user.id)
    # Newest requests appear first in the queue.
    return query.order_by(Request.created_at.desc()).all()
    
@router.get("/{request_id}", response_model=RequestResponse)
def get_request(
    request_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Fetch one request, enforcing ownership for client accounts."""
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Knowing or guessing another request ID does not grant access to its details.
    if current_user.role == UserRole.client and request.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to view this request")

    return request


@router.patch("/{request_id}/status", response_model=RequestResponse)
def update_request_status(
    request_id: int,
    payload: RequestUpdateStatus,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Ask the workflow service to validate and save one status transition."""
    request = db.get(Request, request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return change_request_status(
        db=db,
        request=request,
        new_status=payload.status,
        user=current_user,
        note=payload.note,
    )
