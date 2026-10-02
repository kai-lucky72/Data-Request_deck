"""Admin-only user management endpoints required for staff account control."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, UserRoleUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    """List all accounts; admin only."""
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    """Create a new account; this route is restricted to administrators."""
    # Normalize email so `Person@Example.com` and `person@example.com` do not
    # become separate accounts even if the database collation is case-sensitive.
    email = str(payload.email).lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email is already registered")
    # The password field is transformed into a one-way hash before ORM storage.
    user = User(email=email, name=payload.name, role=payload.role,
                organisation=payload.organisation, password_hash=hash_password(payload.password), is_active=True)
    db.add(user)  # Stage a new row in this database session.
    db.commit()  # Write it to the database and finish the transaction.
    db.refresh(user)  # Load database-generated values such as id and created_at.
    return user


@router.patch("/{user_id}/active", response_model=UserResponse)
def set_user_active(
    user_id: int,
    active: bool,
    db: Annotated[Session, Depends(get_db)],
    current_admin: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    """Change whether a user can log in, while retaining their historical records."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    # Prevent an administrator from immediately locking themselves out.
    if user.id == current_admin.id and not active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    user.is_active = active  # The auth dependency checks this flag on every request.
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Annotated[Session, Depends(get_db)],
    _admin: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    """Change account permissions; only an administrator can reach this route."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    # UserRoleUpdate validation has already restricted the request to known roles.
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user
