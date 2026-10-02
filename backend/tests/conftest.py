"""Shared fixtures for all tests."""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.assignment import Assignment
from app.models.episode import Episode, Quality
from app.models.request import Request, RequestStatus
from app.models.user import User, UserRole


@pytest.fixture
def db():
    """Give each test a fresh in-memory relational database and ORM session."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def make_users_and_request(db, status=RequestStatus.in_progress):
    """Create linked actor/request rows so foreign-key relationships are real."""
    client = User(email="client@test.com", password_hash="hash", role=UserRole.client, name="Client", is_active=True)
    operator = User(email="ops@test.com", password_hash="hash", role=UserRole.operator, name="Ops", is_active=True)
    db.add_all([client, operator]); db.commit()
    request = Request(client_id=client.id, task_name="pick cup", episodes_requested=1,
                      deadline=date(2026, 12, 1), status=status)
    db.add(request); db.commit()
    return client, operator, request
