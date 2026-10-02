"""Domain rules for linking usable, unassigned episodes to requests."""

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.episode import Episode, Quality
from app.models.request import Request, RequestStatus
from app.models.user import User


def assign_episode_to_request(db: Session, request: Request, episode: Episode, user: User) -> Assignment:
    """Validate episode/request eligibility, persist the link, and return it."""
    # Delivery and later states are frozen so their delivered dataset is stable.
    if request.status not in {RequestStatus.submitted, RequestStatus.in_progress, RequestStatus.rejected}:
        raise HTTPException(status_code=409, detail="Episodes can only be assigned before delivery")
    if episode.quality not in {Quality.good, Quality.usable}:
        raise HTTPException(status_code=400, detail="Only good or usable episodes can be assigned")
    if episode.assignment is not None:
        raise HTTPException(status_code=409, detail="Episode is already assigned")

    # The unique constraint on episode_id protects this rule from concurrent requests.
    assignment = Assignment(
        request_id=request.id,
        episode_id=episode.id,
        assigned_by_id=user.id,
    )
    db.add(assignment)
    try:
        db.commit()
    except IntegrityError as error:
        # Another operator may have assigned this episode after our earlier check.
        db.rollback()
        raise HTTPException(status_code=409, detail="Episode is already assigned") from error
    db.refresh(assignment)
    return assignment
