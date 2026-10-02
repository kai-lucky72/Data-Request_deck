"""Tests for server-side role dependencies used by protected API routes."""

import pytest
from fastapi import HTTPException

from app.api.deps import require_roles
from app.models.user import User, UserRole


def _user(role: UserRole) -> User:
    return User(email=f"{role.value}@test.com", password_hash="hash", role=role, name=role.value)


def test_operator_and_admin_can_use_operator_routes():
    """The operations allow-list accepts both staff roles."""
    allow_operations = require_roles(UserRole.operator, UserRole.admin)
    operator = _user(UserRole.operator)
    admin = _user(UserRole.admin)

    assert allow_operations(operator) is operator
    assert allow_operations(admin) is admin


def test_client_cannot_use_operator_routes():
    """Client accounts are denied operator-only API access on the server."""
    allow_operations = require_roles(UserRole.operator, UserRole.admin)

    with pytest.raises(HTTPException) as error:
        allow_operations(_user(UserRole.client))

    assert error.value.status_code == 403


def test_only_admin_can_use_user_management_routes():
    """Operator accounts cannot call admin-only user management endpoints."""
    allow_admin = require_roles(UserRole.admin)
    assert allow_admin(_user(UserRole.admin)).role == UserRole.admin

    with pytest.raises(HTTPException) as error:
        allow_admin(_user(UserRole.operator))

    assert error.value.status_code == 403
