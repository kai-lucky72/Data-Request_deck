"""Validated user, login-token, and safe response shapes."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole

class UserBase(BaseModel):
    """Fields shared by account input and safe user output schemas."""

    email: EmailStr  
    name: str  
    role: UserRole  
    organisation: Optional[str] = None  

class UserCreate(UserBase):
    """Fields accepted by the admin endpoint when creating an account."""

    password: str

class UserRoleUpdate(BaseModel):
    """Request body for an admin role change."""

    role: UserRole
    
class UserResponse(UserBase):
    """Safe public profile fields returned by user and auth endpoints."""

    id: int
    is_active: bool
    created_at: datetime
    
    # Allow Pydantic to read properties directly from a SQLAlchemy User object.
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    """Standard OAuth2 response body returned after successful login."""

    access_token: str  # Signed JWT that clients send in the Authorization header.
    token_type: str = "bearer"  # Tells clients how to present the token.

class LoginRequest(BaseModel):
    """JSON login shape kept for clients that do not use Swagger's OAuth form."""

    email: EmailStr  # Account lookup key.
    password: str  # Compared with the stored password hash, never stored as-is.
    