"""User model."""

from orm.core.model import BaseModel
from orm.core.utils import Relationship, get_foreign_key
from orm.models.email import Email
from sqlmodel import Field, ForeignKey


class User(BaseModel, table=True):
    """Store primary user identity information."""

    __tablename__ = "user"

    username: str = Field(index=True, unique=True, nullable=False, max_length=100)
    display_name: str | None = Field(default=None, max_length=160)
    is_active: bool = Field(default=True, index=True)
    primary_email_id: int | None = Field(
        default=None,
        index=True,
        sa_column_args=(ForeignKey(get_foreign_key(Email)),),
    )
    primary_email = Relationship(Email, optional=True)

    @staticmethod
    def normalize_username(value: str) -> str:
        """Normalize username before persistence."""
        return value.strip().lower()

    def set_username(self, value: str) -> None:
        """Set and normalize a username."""
        normalized = self.normalize_username(value)
        if not normalized:
            msg = "Username cannot be empty."
            raise ValueError(msg)
        self.username = normalized

    def activate(self) -> None:
        """Activate this user account."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate this user account."""
        self.is_active = False

    def set_primary_email(self, email_id: int | None) -> None:
        """Set or clear the primary email reference."""
        self.primary_email_id = email_id
