from datetime import datetime,timezone
from typing import Optional

from sqlalchemy import Integer, String, Boolean, Column, DateTime, Enum as SAEnum
from sqlalchemy.orm import mapped_column, Mapped,Mapped
import enum

from app.db.base import Base

class UserRole(str, enum.Enum):
    """Defines the different roles that a user can have in the system."""
    client = "client"
    operator = "operator"
    admin = "admin"

class User(Base):
    """
    User model: maps user accounts to the database.
    This class defines columns for the user's unique ID, email address, and password hash.
    Each attribute is mapped to a column in the 'user' table.
    """
    id: Mapped[int] = mapped_column(primary_key=True)  # Unique identifier for the user (Primary Key)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)  # Email address (must be unique)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # Hashed password
    role:Mapped[UserRole] = mapped_column(SAEnum(UserRole),nullable=False)
    name:Mapped[str] = mapped_column(String(255),nullable=False)
    organisation:Mapped[Optional[str]]=mapped_column(String(255),nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean,default=True,nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )