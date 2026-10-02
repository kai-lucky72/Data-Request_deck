"""Tests for episode assignment logic and constraints."""

from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.assignment import Assignment
from app.models.episode import Episode, Quality
from app.models.request import Request, RequestStatus
from app.models.user import User, UserRole
from app.services.assignments import assign_episode_to_request
from tests.conftest import make_users_and_request


def test_episode_cannot_be_assigned_twice(db):
    """The database unique constraint is the final guard against episode reuse."""
    client, operator, first_request = make_users_and_request(db)
    second_request = Request(client_id=client.id, task_name="other task", episodes_requested=1,
                             deadline=date(2026, 12, 1), status=RequestStatus.in_progress)
    episode = Episode(episode_id="EP-1", robot_id="ARM-1", task_name="pick cup",
                      recorded_at=datetime(2026, 9, 1, tzinfo=timezone.utc), duration_seconds=20,
                      quality=Quality.good)
    db.add_all([second_request, episode]); db.commit()
    db.add(Assignment(request_id=first_request.id, episode_id=episode.id, assigned_by_id=operator.id)); db.commit()
    db.add(Assignment(request_id=second_request.id, episode_id=episode.id, assigned_by_id=operator.id))
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


def test_bad_quality_episode_cannot_be_assigned(db):
    """Bad recordings remain searchable but cannot enter a client delivery."""
    _client, operator, request = make_users_and_request(db)
    episode = Episode(episode_id="EP-BAD", robot_id="ARM-1", task_name="pick cup",
                      recorded_at=datetime(2026, 9, 1, tzinfo=timezone.utc), duration_seconds=20,
                      quality=Quality.bad)
    db.add(episode); db.commit()
    with pytest.raises(HTTPException) as error:
        assign_episode_to_request(db, request, episode, operator)
    assert error.value.status_code == 400


def test_usable_episode_can_be_assigned_once(db):
    """A usable recording is accepted, but a second assignment gets a clear conflict."""
    _client, operator, request = make_users_and_request(db)
    episode = Episode(episode_id="EP-USE", robot_id="ARM-1", task_name="pick cup",
                      recorded_at=datetime(2026, 9, 1, tzinfo=timezone.utc), duration_seconds=20,
                      quality=Quality.usable)
    db.add(episode)
    db.commit()

    first = assign_episode_to_request(db, request, episode, operator)
    assert first.request_id == request.id

    with pytest.raises(HTTPException) as error:
        assign_episode_to_request(db, request, episode, operator)
    assert error.value.status_code == 409
