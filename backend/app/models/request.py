from datetime import datetime,timezone
from typing import Optional

from sqlalchemy import Integer,String,DateTime,Enum as SAEnum
from sqlalchemy.orm import Mapped,mapped_column,ForeignKey
import enum

from app.db.base import Base

class RequestStatus(str,enum.Enum):
    """Defines the possible status values that a request can have in the system."""
    in_progress = "in_progress"
    delivered = "delivered"
    accepted = "accepted"
    rejected = "rejected"


class Request(Base):
    """
    The Request class maps to the 'requests' table in the database.
    Every instance of this class will correspond to a row in the 'requests' table, and each class attribute that uses 'mapped_column' will become a column in that table.
    This approach provides clear, explicit mapping between Python code and the underlying relational database, supporting ORM querying and database integrity.
    """
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The client_id field establishes a foreign key relationship to the 'id' column of the 'user' table.
    # This links each request to a specific client user account, enforcing integrity at the database level.
    # By referencing user.id, it allows us to easily query which user (client) created this request and ensures requests cannot exist without a valid client.
    client_id: Mapped[str] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)

    task_name: Mapped[str] = mapped_column(String(255), nullable=False) 
    episodes_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        SAEnum(RequestStatus), # Convert the Python enum to a database enum representation.
        default=RequestStatus.submitted,
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) #Automatically set the value to the current UTC time when a new row is created.
        nullable=False
    )
     updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),  # Set current UTC time when inserted.
        onupdate=lambda: datetime.now(timezone.utc),  # Automatically update the value whenever the row is changed.
        nullable=False  
    )