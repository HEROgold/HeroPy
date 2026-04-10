"""Email model."""

from datetime import UTC, datetime

from sqlmodel import Field

from herogold.orm.core.model import BaseModel


class Email(BaseModel, table=True):
    """Store an email address and verification state."""

    __tablename__ = "email"

    email: str = Field(index=True, unique=True, nullable=False, max_length=320)
    is_verified: bool = Field(default=False, index=True)
    verified_at: datetime | None = Field(default=None)

    @staticmethod
    def normalize(value: str) -> str:
        """Normalize an email address before storage."""
        return value.strip().lower()

    def set_email(self, value: str) -> None:
        """Set and normalize the email field in-place."""
        normalized = self.normalize(value)
        if not normalized:
            msg = "Email cannot be empty."
            raise ValueError(msg)
        self.email = normalized

    def mark_verified(self) -> None:
        """Mark this email as verified using the current UTC timestamp."""
        self.is_verified = True
        self.verified_at = datetime.now(UTC)

    def clear_verification(self) -> None:
        """Clear verification status for this email."""
        self.is_verified = False
        self.verified_at = None
