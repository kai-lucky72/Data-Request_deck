"""Operator API for importing, finding, and assigning dataset episodes."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.episode import Episode, Quality
from app.models.request import Request
from app.models.user import User, UserRole
from app.schemas.episode import AssignmentCreate, AssignmentResponse, EpisodeResponse, ImportReport
from app.services.import_episodes import import_episodes
from app.services.assignments import assign_episode_to_request


router = APIRouter(
    prefix="/episodes",
    tags=["Episodes"]
)

# One reusable allow-list keeps episode tools restricted to operations staff.
OPERATOR_ROLES = (UserRole.operator, UserRole.admin)

@router.post("/import", response_model=ImportReport)
async def upload_episode_csv(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_roles(*OPERATOR_ROLES))],# Only operators and admins can import episodes
    file: UploadFile = File(...),
):
    """Receive an operator's CSV file and send its contents to the importer."""
    # Reject a clearly wrong file before writing it to temporary storage.
    if not file.filename or Path(file.filename).suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail="Upload a .csv file")
    # The importer accepts a file path, so save this upload temporarily; `finally`
    # guarantees cleanup even if CSV parsing or a database operation fails.
    import tempfile

    temporary_path: Path | None = None # Temporary file path
    try:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(await file.read())
        # Return the full report so the operator can repair rows listed in `issues`.
        return import_episodes(db, temporary_path)
    finally:
        await file.close()
        if temporary_path:
            temporary_path.unlink(missing_ok=True)



@router.get("", response_model=list[EpisodeResponse])
def list_episodes(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(require_roles(*OPERATOR_ROLES))], # Only operators and admins can list episodes
    task_name: str | None = Query(default=None),
    quality: Quality | None = Query(default=None),
    available_only: bool = Query(default=True),
):
    """Search the episode catalog with optional task and quality filters."""
    query = db.query(Episode)  # Build a SQL query; rows are fetched only after filters apply.
    if task_name:
        # ilike is a case-insensitive substring match in PostgreSQL and SQLite.
        query = query.filter(Episode.task_name.ilike(f"%{task_name.strip()}%"))
    if quality:
        # Enum query values are validated by FastAPI before this function executes.
        query = query.filter(Episode.quality == quality)
    if available_only:
        # `has()` becomes a NOT EXISTS query, avoiding an in-Python full-table filter.
        query = query.filter(~Episode.assignment.has())
    # Limit results to keep the first version of the browser UI responsive.
    episodes = query.order_by(Episode.recorded_at.desc()).limit(200).all()
    # Return a simple boolean alongside the episode to make the UI easier to build.
    return [EpisodeResponse.model_validate(ep).model_copy(update={"assigned": ep.assignment is not None}) for ep in episodes]



@router.post("/requests/{request_id}/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_episode(
    request_id: int,
    payload: AssignmentCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_roles(*OPERATOR_ROLES))],# Only operators and admins can assign episodes
):
    """Look up both records, then delegate business rules to the assignment service."""
    # Separate 404 errors tell the operator which of the two requested records is missing.
    request = db.get(Request, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    episode = db.get(Episode, payload.episode_id)
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    # The service verifies request state, episode quality, and duplicate assignment.
    return assign_episode_to_request(db, request, episode, current_user)

@router.get("/requests/{request_id}/assignments", response_model=list[EpisodeResponse])
def list_request_episodes(
    request_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """List a request's episodes for operations staff or its owning client."""
    request = db.get(Request, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role == UserRole.client and request.client_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to view this request")
    # The ORM relationship follows Assignment rows to their linked Episode records.
    return [link.episode for link in request.assignments]
