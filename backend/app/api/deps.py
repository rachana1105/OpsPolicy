"""Shared FastAPI dependencies."""
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AuthError, ForbiddenError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.org import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthError("Authentication required.")
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise AuthError("Invalid or expired token.")
    user = db.get(User, payload.get("sub"))
    if not user:
        raise AuthError("User no longer exists.")
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if roles and user.role.value not in roles:
            raise ForbiddenError(
                "You do not have permission to perform this action.",
                details={"required_roles": list(roles), "your_role": user.role.value},
            )
        return user

    return checker
