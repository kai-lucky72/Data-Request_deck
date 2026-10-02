"""Login endpoint and authenticated current-user endpoint."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password, create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import Token, UserResponse
from app.api.deps import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

@router.post("/login", response_model=Token)
def login(
    # FastAPI injects a request-scoped database connection and form fields.
    db: Annotated[Session, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    """Check credentials and issue a signed bearer token when the account is active."""
    # OAuth2 names the login field `username`; this app uses that slot for email.
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Use the same error for unknown emails and wrong passwords so login does not
    # reveal which email addresses have accounts.
    if not user or not verify_password(form_data.password,user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate":"Bearer"},
        )
    # Keep this check outside the invalid-password branch: inactive accounts must
    # never receive a token even when their password is correct.
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
            
    # The JWT subject stores the user ID as text, as required by JWT conventions.
    # Role is included as context, but protected routes reload current role from DB.
    access_token = create_access_token(
        data={"sub":str(user.id), "role":user.role.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    
    return {"access_token":access_token, "token_type":"bearer"}

@router.get("/me", response_model=UserResponse)
def read_current_user(
    # get_current_user validates the token and looks up the active account.
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return the profile associated with the request's bearer token."""
    return current_user