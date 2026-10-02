from datetime import datetime,timezone
from typing import Optional

from sqlalchemy import Integer,String,DateTime,Enum as SAEnum
from sqlalchemy.orm import Mapped,mapped_column
import enum

from app.db.base import Base

class Quality(str,enum.Enum):
    """Defines the different quality levels that an episode can have."""
    good = "good"    
    usable = "usable"
    bad = "bad"      


class Episode(Base):
    """
    The Episode class maps to the 'episodes' table in the database.
    Each attribute of this class corresponds to a column in the table.
    The __tablename__ attribute explicitly sets the table name for SQLAlchemy ORM.
    """
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    robot_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False
    )
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False) 
    operator_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quality: Mapped[Quality] = mapped_column(SAEnum(Quality), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) #Automatically set the value to the current UTC time when a new row is created.
        nullable=False
    )
    
     # This allows each Episode object to access its related Assignment via the `.assignment` attribute.
    # The `Assignment` model has a corresponding `episode` relationship with `back_populates="assignment"` to form a bidirectional one-to-one link.
    # Because the Assignment table has a unique constraint on the `episode_id`, each Episode can have at most one Assignment, making this a strict one-to-one mapping.
    assignment = relationship("Assignment", back_populates="episode", uselist=False) 