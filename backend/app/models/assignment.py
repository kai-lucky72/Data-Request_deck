"""ORM model linking an episode to the request it helps fulfil."""

from datetime import datetime,timezone
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped,mapped_column,relationship

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

    # - `request`: This sets up a relationship to the Request model. The `back_populates="assignments"` parameter means that
    #   each Request object can access a list of all related Assignment objects through a .assignments attribute. It establishes
    #   a bidirectional link, enabling you to easily go from Assignment to its parent Request and back.
    request =relationship("Request",back_populates="assignments")
    
    # - `episode`: This sets up a relationship to the Episode model. Here, `back_populates="assignment"` indicates each Episode
    #   has (at most) one related Assignment accessed via .assignment. Because Assignment.episode_id is unique, this is a
    #   one-to-one relationship from Assignment to Episode (an episode can only appear in at most one assignment).
    episode = relationship("Episode",back_populates="assignment")
    
    # - `assigned_by`: This relates the assignment to the User who performed the assignment (typically an operator or admin).
    #   No `back_populates` is given, so the connection is only from Assignment to User; you can access the assigning user
    #   via Assignment.assigned_by. This supports auditing, showing who made the assignment.
    assigned_by = relationship("User")
    
    
    
    

    