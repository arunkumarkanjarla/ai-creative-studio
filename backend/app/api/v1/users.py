
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.user import User

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse
)

from app.core.security import hash_password
from app.api.v1.dependencies import require_admin


router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)]
):

    return db.query(User).order_by(User.id.desc()).all()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_user(
    data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)]
):

    email = str(data.email).lower()

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    user = User(
        name=data.name,
        email=email,
        mobile=data.mobile,
        password_hash=hash_password(data.password),
        role="user",
        can_access_image=data.can_access_image,
        can_access_audio=data.can_access_audio,
        can_access_video=data.can_access_video,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)]
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)]
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Do not allow changing administrator accounts here.
    if user.role == "systemadministrator":
        raise HTTPException(
            status_code=403,
            detail="Administrator accounts cannot be edited here"
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return user
