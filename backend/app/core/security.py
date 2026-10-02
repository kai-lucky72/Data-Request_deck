from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError,jwt
import bcrypt

from app.core.config import settings

def hash_password(password:str) -> str:
    """Hash a password with bcrypt and return its database-safe text form"""
    # bcrypt salts each hash automatically, so identical passwords produce
    # different stored strings and cannot be compared by a simple equality check
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password:str, hashed_password:str) ->bool:
    """Check a password against hashes created by bcrypt or Passlib's bcrypt."""
    try:
        # bcrypt.checkpw() understands the stored format automatically
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        # Badly formatted hashes or passwords beyond bcrypt's byte limit fail closed.
        return False


def create_access_token(data:dict, expires_delta:Optional[timedelta]=None) -> str:
    """Create a JWT access token for the given data."""
    to_encode =data.copy() #create a copy of the data to avoid modifying the original dictionary
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))  # Calculate the expiration time for the token, defaulting to the configured access token expiration time.
    to_encode.update({"exp":expire}) # Add the expiration time to the data to be encoded
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM) # Encode the data and return the token.
    return encoded_jwt

def decode_access_token(token:str) -> dict | None:
    """Decode a JWT access token and return the data."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]) # Decode the token and return the payload.
        return payload
    except JWTError:
        return None # return none to indicate invalid token or expired token.
        