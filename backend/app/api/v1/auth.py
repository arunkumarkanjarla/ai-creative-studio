
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
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
from app.core.analytics import track_login_attempt, get_client_ip


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    username = form_data.username.lower()
    user = db.query(User).filter(
        User.email == username
    ).first()
    
    # Extract IP and user agent for tracking
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = get_client_ip(request, forwarded_for)
    user_agent = request.headers.get("User-Agent")

    if not user:
        # Track failed login - unknown user
        track_login_attempt(
            db=db,
            username=username,
            user_id=None,
            ip=ip,
            user_agent=user_agent,
            status="failed",
            failure_reason="unknown_user"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        # Track failed login - inactive account
        track_login_attempt(
            db=db,
            username=username,
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
            status="failed",
            failure_reason="inactive_account"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not verify_password(form_data.password, user.password_hash):
        # Track failed login - wrong password
        track_login_attempt(
            db=db,
            username=username,
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
            status="failed",
            failure_reason="wrong_password"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Track successful login
    track_login_attempt(
        db=db,
        username=username,
        user_id=user.id,
        ip=ip,
        user_agent=user_agent,
        status="success",
        failure_reason=None
    )

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    # Update last_seen_at periodically (throttled to ~1/min to reduce DB load)
    # This is a simple implementation - could be optimized with caching
    from app.models.analytics import LoginSession
    now = datetime.utcnow()
    
    try:
        # Find the most recent active session for this user
        active_session = db.query(LoginSession).filter(
            LoginSession.user_id == current_user.id,
            LoginSession.status == "success",
            LoginSession.logout_at.is_(None)
        ).order_by(LoginSession.login_at.desc()).first()
        
        if active_session:
            # Only update if more than 1 minute has passed
            if not active_session.last_seen_at or (now - active_session.last_seen_at).total_seconds() > 60:
                active_session.last_seen_at = now
                db.commit()
    except Exception as e:
        print(f"[Auth] Failed to update last_seen_at: {e}")
        db.rollback()
    
    return current_user


@router.post("/logout")
def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    """Mark the current user session as logged out."""
    from app.models.analytics import LoginSession
    now = datetime.utcnow()
    
    try:
        # Find the most recent active session for this user
        active_session = db.query(LoginSession).filter(
            LoginSession.user_id == current_user.id,
            LoginSession.status == "success",
            LoginSession.logout_at.is_(None)
        ).order_by(LoginSession.login_at.desc()).first()
        
        if active_session:
            active_session.logout_at = now
            active_session.status = "logged_out"
            
            # Calculate duration in seconds
            login_time = active_session.last_seen_at or active_session.login_at
            duration_seconds = int((now - login_time).total_seconds())
            active_session.duration = duration_seconds
            
            db.commit()
            
            return {
                "message": "Logged out successfully",
                "session_duration_seconds": duration_seconds
            }
        else:
            return {"message": "No active session found"}
    
    except Exception as e:
        print(f"[Auth] Failed to logout: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


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
