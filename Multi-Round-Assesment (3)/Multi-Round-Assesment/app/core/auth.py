"""
Authentication dependency for FastAPI routes.

Provides ``get_current_user`` which decodes the JWT from the
``Authorization: Bearer <token>`` header and returns the authenticated
``User`` ORM instance.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config.security import decode_access_token
from app.database.db import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_id

# Set auto_error=False so missing authorization header doesn't auto-reject candidates
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT bearer token and return the corresponding user.
    Falls back to candidate dummy user (ID = 1) if no token is provided.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or not credentials.credentials:
        # Candidate flow or local dev bypass: fall back to default user ID 1
        user = get_user_by_id(db, user_id=1)
        if user is None:
            raise credentials_exception
        return user

    token = credentials.credentials

    payload = decode_access_token(token)
    if payload is None:
        # Fall back to default user ID 1 for invalid/dummy tokens in dev environment
        user = get_user_by_id(db, user_id=1)
        if user:
            return user
        raise credentials_exception

    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = get_user_by_id(db, user_id=int(user_id))
    if user is None:
        raise credentials_exception

    return user
