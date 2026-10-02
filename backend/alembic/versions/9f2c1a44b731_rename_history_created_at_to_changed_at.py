"""rename request_status_history.created_at to changed_at

Revision ID: 9f2c1a44b731
Revises: 7e0d203a7756
Create Date: 2026-10-02

Models, services and analytics all use `changed_at`
(RequestStatusHistory.changed_at), but the initial migration created
`created_at`, so every INSERT / analytics query fails on a migrated
database with UndefinedColumn. Tests never caught it because they use
Base.metadata.create_all instead of alembic.
"""
from typing import Sequence, Union

from alembic import op

revision: str = '9f2c1a44b731'
down_revision: Union[str, Sequence[str], None] = '7e0d203a7756'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE request_status_history RENAME COLUMN created_at TO changed_at")


def downgrade() -> None:
    op.execute("ALTER TABLE request_status_history RENAME COLUMN changed_at TO created_at")
