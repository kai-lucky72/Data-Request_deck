"""Reusable authentication and role dependencies for protected API routes."""

from typing import Annotated

from fastapi import Depends,HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User,UserRole


# OAuth2PasswordBearer reads `Authorization: Bearer ...` from a request and also
# tells Swagger UI where users can obtain a token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Validate the bearer token and return its active database user."""
    # Reuse one generic error to avoid revealing whether an account exists.
    credentials_exception=HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Couldnt validate credentials",
        headers={"WWW-Authenticate":"Bearer"},
    )

    # Decoding checks signature and expiry; invalid tokens return None.
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    subject = payload.get("sub")

    try:
        # Convert the subject (user ID) to an integer
        user_id = int(subject)
    except (TypeError, ValueError):
        raise credentials_exception

    # Look the user up on every request so deactivation or role changes take effect
    # immediately instead of trusting old token claims until token expiration.
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user

def require_roles(*roles:UserRole):
    """Build a FastAPI dependency that permits only the listed user roles."""
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        # This second dependency layer first authenticates, then checks authorization.
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="you dont have permission to perform this action",
            )
        return current_user
    return role_checker