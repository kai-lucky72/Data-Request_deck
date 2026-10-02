"""ORM model linking an episode to the request it helps fulfil."""

from datetime import datetime,timezone
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped,mapped_column

from app.db.base import Base

class Assignment(Base):
    """
    The Assignment class represents the 'assignments' table in the database.
    Each instance corresponds to a row that links an episode to the request it fulfills.
    The 'id' field is the primary key for this table, providing a unique identifier for each assignment.
    """
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)

    # Many assignment rows may belong to one request, hence this foreign key is indexed.
    request_id:Mapped[int]=mapped_column(ForeignKey("requests.id"),nullable=False,index=True)

    # Unique=True adds a database constraint so an episode cannot be assigned twice.
    # This first version has no release action, so uniqueness lasts for the row's lifetime.
    episode_id:Mapped[int]=mapped_column(ForeignKey("episodes.id"),nullable=False,unique=True)

    # Keep the assigning user's ID so operations actions can be audited later.
    assigned_by_id:Mapped[int]=mapped_column(ForeignKey("users.id"),nullable=False)
    
    assigned_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),
        default=lambda:datetime.now(timezone.utc),
        nullable=False
    )
    
    