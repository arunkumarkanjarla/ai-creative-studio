
from typing import Annotated, Optional

import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.user import User


# Required login
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)

# Optional login (guests allowed)
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def _user_from_token(token: str, db: Session) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
        user_id = int(user_id)
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise credentials_exception

    return user


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    return _user_from_token(token, db)


def get_optional_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme_optional)],
    db: Annotated[Session, Depends(get_db)],
) -> Optional[User]:
    """Return the logged-in user, or None for guests."""
    if not token:
        return None

    try:
        return _user_from_token(token, db)
    except HTTPException:
        return None


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role != "systemadministrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user


def require_studio_access(studio: str):
    permission_map = {
        "image": "can_access_image",
        "audio": "can_access_audio",
        "video": "can_access_video",
    }

    if studio not in permission_map:
        raise ValueError("Invalid studio")

    def check_permission(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role == "systemadministrator":
            return current_user

        if not getattr(current_user, permission_map[studio]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{studio.title()} Studio access denied",
            )

        return current_user

    return check_permission
