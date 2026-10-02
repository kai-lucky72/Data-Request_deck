"""Tests for request status workflow and permissions."""

import pytest
from fastapi import HTTPException

from app.models.request import RequestStatus
from app.models.user import User, UserRole
from app.services.status import change_request_status
from tests.conftest import make_users_and_request


def test_operator_cannot_deliver_before_requested_episode_count(db):
    """Delivery is blocked until assignments reach the request quantity."""
    _client, operator, request = make_users_and_request(db)
    with pytest.raises(HTTPException) as error:
        change_request_status(db, request, RequestStatus.delivered, operator)
    assert error.value.status_code == 400


def test_only_request_owner_can_accept_delivery(db):
    """A client cannot accept another client's delivered request."""
    client, operator, request = make_users_and_request(db, RequestStatus.delivered)
    other = User(email="other@test.com", password_hash="hash", role=UserRole.client, name="Other", is_active=True)
    db.add(other); db.commit()
    with pytest.raises(HTTPException) as error:
        change_request_status(db, request, RequestStatus.accepted, other)
    assert error.value.status_code == 403


def test_only_operator_can_start_request(db):
    """Clients cannot perform the operations-owned submitted transition."""
    client, operator, request = make_users_and_request(db, RequestStatus.submitted)
    with pytest.raises(HTTPException) as error:
        change_request_status(db, request, RequestStatus.in_progress, client)
    assert error.value.status_code == 403

    changed = change_request_status(db, request, RequestStatus.in_progress, operator)
    assert changed.status == RequestStatus.in_progress


def test_operator_cannot_accept_client_delivery(db):
    """Only the client role may accept a delivered request."""
    _client, operator, request = make_users_and_request(db, RequestStatus.delivered)
    with pytest.raises(HTTPException) as error:
        change_request_status(db, request, RequestStatus.accepted, operator)
    assert error.value.status_code == 403


def test_request_owner_can_accept_and_status_change_is_audited(db):
    """The owning client can accept delivery and the change records its actor."""
    client, _operator, request = make_users_and_request(db, RequestStatus.delivered)
    changed = change_request_status(db, request, RequestStatus.accepted, client)
    history = request.status_history[-1]
    assert changed.status == RequestStatus.accepted
    assert history.from_status == RequestStatus.delivered
    assert history.to_status == RequestStatus.accepted
    assert history.changed_by_id == client.id


def test_invalid_status_transition_is_rejected(db):
    """Accepted requests are terminal and cannot be moved back to work."""
    _client, operator, request = make_users_and_request(db, RequestStatus.accepted)
    with pytest.raises(HTTPException) as error:
        change_request_status(db, request, RequestStatus.in_progress, operator)
    assert error.value.status_code == 400
