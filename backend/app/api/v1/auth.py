
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister
from app.core.security import (
    verify_password,
    create_access_token,
    hash_password
)
from app.schemas.user import TokenResponse, UserResponse
from app.api.v1.dependencies import get_current_user


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):

    user = db.query(User).filter(
        User.email == form_data.username.lower()
    ).first()

    if (
        not user
        or not user.is_active
        or not verify_password(
            form_data.password,
            user.password_hash
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)]
):

    return current_user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    email = user_data.email.lower()

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    new_user = User(
        name=user_data.name.strip(),
        email=email,
        mobile=user_data.mobile,
        password_hash=hash_password(user_data.password),
        role="user",
        can_access_image=False,
        can_access_audio=False,
        can_access_video=False,
        is_active=True,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "message": "Account created successfully. Please sign in.",
            "user_id": new_user.id,
            "email": new_user.email,
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create account. Please try again.",
        )
