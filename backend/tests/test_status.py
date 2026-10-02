"""Tests for request status workflow and permissions."""

import pytest
from fastapi import HTTPException

from app.models.request import RequestStatus
from app.models.user import User
from app.services.status import change_request_status
from conftest import make_users_and_request


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
