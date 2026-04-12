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

@router.get("/verify-email")
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    """
    Verify a user's email address using the UUID token from the registration email.
    Activates the account (is_active=True, is_verified=True) and clears the token.
    """
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already-used verification token.",
        )

    user.is_verified = True
    user.is_active = True
    user.verification_token = None
    db.commit()

    return {"message": "Email verified successfully. You can now log in."}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a JWT access token + refresh token pair.
    Stores a bcrypt hash of the refresh token for rotation validation.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not activated. Please verify your email first.",
        )

    access_token = create_access_token({"sub": user.id, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": user.id})

    # Store hashed refresh token — enables reuse detection during rotation
    user.refresh_token_hash = hash_password(refresh_token)
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
