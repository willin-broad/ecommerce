import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class UserRole(str, enum.Enum):
    customer = "customer"
    admin = "admin"


class User(Base):
    """
    SQLAlchemy ORM model for the users table.

    - Passwords are stored as bcrypt hashes — never plaintext.
    - Refresh tokens are stored as bcrypt hashes to detect token reuse.
    - Email verification and password reset use UUID tokens (single-use).
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, native_enum=False), default=UserRole.customer, nullable=False
    )

    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Email verification (UUID token, cleared after use)
    verification_token: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )

    # Password reset (UUID token with expiry)
    reset_token: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    reset_token_expires: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    # Hashed refresh token for rotation/revocation
    refresh_token_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
