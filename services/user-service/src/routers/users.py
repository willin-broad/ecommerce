import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_admin
from ..models.user import User
from ..schemas.user import RoleUpdateRequest, UserResponse, UserUpdateRequest
from ..services.email import send_email
from ..config import get_settings

router = APIRouter(prefix="/api/users", tags=["users"])
settings = get_settings()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the currently authenticated user's own profile.
    If email is changed, the account is re-flagged for verification and a new
    verification email is dispatched. The user stays active so they don't lose access.
    """
    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    if payload.email is not None and payload.email != current_user.email:
        # Uniqueness check — reject if another account already owns this email
        taken = (
            db.query(User)
            .filter(User.email == payload.email, User.id != current_user.id)
            .first()
        )
        if taken:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That email address is already in use.",
            )

        new_token = str(uuid.uuid4())
        current_user.email = payload.email
        current_user.is_verified = False
        current_user.is_active = True  # Stay active so they don't lose access immediately
        current_user.verification_token = new_token
        current_user.refresh_token_hash = None  # Revoke all sessions — email change is sensitive

        verify_url = f"{settings.APP_BASE_URL}/api/auth/verify-email?token={new_token}"
        await send_email(
            to=payload.email,
            subject="Confirm your new email — eCommerce Platform",
            body=(
                f"Hi {current_user.full_name},\n\n"
                f"Please verify your new email address:\n\n"
                f"  {verify_url}\n\n"
                f"— eCommerce Platform"
            ),
        )

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """[Admin] List all users with pagination."""
    return db.query(User).offset(skip).limit(limit).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """[Admin] Fetch a specific user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return user


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_role(
    user_id: str,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """
    [Admin] Promote or demote a user's role (customer ↔ admin).
    An admin cannot change their own role — prevents accidental self-lockout.
    """
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change your own role.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    [Admin] Soft-delete a user by setting is_active=False.
    Hard delete is intentionally avoided to preserve order history integrity.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    user.is_active = False
    user.refresh_token_hash = None  # Immediately revoke active sessions
    db.commit()
