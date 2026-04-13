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


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    The old refresh token is invalidated (refresh token rotation).
    Presenting an already-used refresh token raises 401 (reuse detection).
    """
    token_data = decode_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — refresh token required.",
        )

    user = (
        db.query(User)
        .filter(User.id == token_data.get("sub"), User.is_active == True)  # noqa: E712
        .first()
    )
    if not user or not user.refresh_token_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalid or account inactive.",
        )

    if not verify_password(payload.refresh_token, user.refresh_token_hash):
        # Token reuse detected — invalidate all sessions as a security measure
        user.refresh_token_hash = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected. Please log in again.",
        )

    new_access = create_access_token({"sub": user.id, "role": user.role.value})
    new_refresh = create_refresh_token({"sub": user.id})
    user.refresh_token_hash = hash_password(new_refresh)
    db.commit()

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    """
    Log out by invalidating the refresh token.
    The access token will still be valid until it expires (short TTL mitigates risk).
    """
    try:
        token_data = decode_token(payload.refresh_token)
        user = db.query(User).filter(User.id == token_data.get("sub")).first()
        if user:
            user.refresh_token_hash = None
            db.commit()
    except HTTPException:
        pass  # Already expired tokens are still a valid logout


@router.post("/forgot-password")
async def forgot_password(
    payload: PasswordResetRequest, db: Session = Depends(get_db)
):
    """
    Initiate a password reset.
    Always returns success to prevent email enumeration attacks.
    The reset token expires in 1 hour.
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if user and user.is_active:
        reset_token = str(uuid.uuid4())
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()

        reset_url = f"{settings.APP_BASE_URL}/api/auth/reset-password?token={reset_token}"
        await send_email(
            to=user.email,
            subject="Password Reset Request — eCommerce Platform",
            body=(
                f"Hi {user.full_name},\n\n"
                f"You requested a password reset. Click the link below:\n\n"
                f"  {reset_url}\n\n"
                f"This link expires in 1 hour. If you didn't request this, ignore this email.\n\n"
                f"— eCommerce Platform"
            ),
        )

    return {
        "message": "If that email is registered and active, a reset link has been sent."
    }


@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """
    Apply a new password using the reset token from the reset email.
    Also invalidates all existing refresh tokens (forces re-login on all devices).
    """
    user = (
        db.query(User)
        .filter(
            User.reset_token == payload.token,
            User.reset_token_expires > datetime.utcnow(),
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    user.hashed_password = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    user.refresh_token_hash = None  # Invalidate all active sessions
    db.commit()

    return {"message": "Password reset successful. Please log in with your new password."}
