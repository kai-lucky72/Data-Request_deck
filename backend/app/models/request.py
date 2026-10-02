from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from ..db.base import Base

class RequestStatus(str,enum.Enum):
    """Defines the possible status values that a request can have in the system."""
    submitted = "submitted"
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
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

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
        default=lambda: datetime.now(timezone.utc), #Automatically set the value to the current UTC time when a new row is created.
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),  # Set current UTC time when inserted.
        onupdate=lambda: datetime.now(timezone.utc),  # Automatically update the value whenever the row is changed.
        nullable=False  
    )
    # The 'client' relationship associates each Request instance with the corresponding User (the client who created the request).
    # 'back_populates="requests"' means that the User model should have a 'requests' relationship/attribute that returns all Request objects linked to that user.
    # This sets up a bidirectional link between Request and User, so from a Request you can access its client via .client,
    # and from a User you can access all their created requests via .requests. This improves queryability and ORM navigation.
    client = relationship("User", back_populates="requests") 

    # The 'assignments' relationship connects each Request to all Assignment records that reference it via their 'request_id' foreign key.
    # With back_populates="request", it forms a bidirectional relationship: from a Request, you can access all its assignments (.assignments);
    # from an Assignment, you can access the associated Request (.request).
    # This means a single request can have multiple Assignment objects (for example, mapping multiple episodes that fulfill the request).
    assignments = relationship("Assignment", back_populates="request")

    # This is an audit trail:
    # you can inspect all previous status changes for this request.
    # Example: `request.status_history` gives you the list of status change records.
    status_history = relationship(  
        "RequestStatusHistory",  
        back_populates="request",
        order_by="RequestStatusHistory.changed_at"  # SQLAlchemy will return these history rows ordered by timestamp.
    )


class RequestStatusHistory(Base):  
    __tablename__ = "request_status_history"  

    id: Mapped[int] = mapped_column(primary_key=True)  

    # This is the real database connection that says:
    # “This status-history row belongs to this request.”
    # Without it, the history record would not know which request it belongs to.
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), nullable=False, index=True)

    from_status: Mapped[Optional[RequestStatus]] = mapped_column(SAEnum(RequestStatus), nullable=True)
    to_status: Mapped[RequestStatus] = mapped_column(SAEnum(RequestStatus), nullable=False)
    
    # Foreign key to the user who changed the status.
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Optional comment explaining why the status changed.


    # - `changed_by`: links this history row to the User who performed the status change, via changed_by_id.
    #   There is no back_populates because User does not currently expose a list of status changes they made.
    #   The one-way link is enough for audit questions such as "who last updated this request's status?"
    changed_by = relationship("User")

    # - `request`: links this history row back to its parent Request. back_populates="status_history"
    #   matches Request.status_history, so request.status_history and history.request stay in sync.
    request = relationship("Request", back_populates="status_history")
    