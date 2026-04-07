import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models.user import User, UserRole
from ..schemas.user import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from ..services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from ..services.email import send_email

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new customer account.
    Sends a console-logged verification email immediately after creation.
    Account is inactive (is_active=False) until the email is verified.
    """
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    verification_token = str(uuid.uuid4())
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.customer,
        is_active=False,
        is_verified=False,
        verification_token=verification_token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    verify_url = (
        f"{settings.APP_BASE_URL}/api/auth/verify-email?token={verification_token}"
    )
    await send_email(
        to=user.email,
        subject="Verify your email — eCommerce Platform",
        body=(
            f"Hi {user.full_name},\n\n"
            f"Thanks for signing up! Please verify your email address:\n\n"
            f"  {verify_url}\n\n"
            f"This link will remain valid until you click it.\n\n"
            f"— eCommerce Platform"
        ),
    )

    return {
        "message": "Registration successful. Check your email to verify your account."
    }

