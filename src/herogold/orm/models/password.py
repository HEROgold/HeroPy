"""Password model with salted PBKDF2 hashing utilities."""

import hashlib
import hmac
import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime
from typing import ClassVar

from orm.core.model import BaseModel
from orm.core.utils import Relationship, get_foreign_key
from orm.models.user import User
from sqlmodel import Field, ForeignKey


class Password(BaseModel, table=True):
    """Store a password hash record for a user."""

    __tablename__ = "password"

    DEFAULT_ALGORITHM: ClassVar[str] = "pbkdf2_sha256"
    DEFAULT_ITERATIONS: ClassVar[int] = 600_000
    MIN_ITERATIONS: ClassVar[int] = 100_000
    MIN_SALT_SIZE: ClassVar[int] = 8

    user_id: int = Field(index=True, sa_column_args=(ForeignKey(get_foreign_key(User)),))
    user = Relationship(User)
    algorithm: str = Field(default=DEFAULT_ALGORITHM, max_length=32)
    iterations: int = Field(default=DEFAULT_ITERATIONS)
    salt: str = Field(nullable=False, max_length=128)
    password_hash: str = Field(nullable=False, max_length=256)
    is_active: bool = Field(default=True, index=True)
    expires_at: datetime | None = Field(default=None, index=True)

    @staticmethod
    def _normalize_plaintext(plaintext: str) -> str:
        """Validate and normalize plaintext password input."""
        if not plaintext:
            msg = "Password cannot be empty."
            raise ValueError(msg)
        return plaintext

    @classmethod
    def generate_salt(cls, size: int = 16) -> str:
        """Generate a URL-safe random salt."""
        if size < cls.MIN_SALT_SIZE:
            msg = f"Salt size must be at least {cls.MIN_SALT_SIZE} bytes."
            raise ValueError(msg)
        return urlsafe_b64encode(secrets.token_bytes(size)).decode("ascii")

    @classmethod
    def derive_hash(cls, plaintext: str, salt: str, iterations: int) -> str:
        """Derive a PBKDF2-HMAC-SHA256 hash from a plaintext password."""
        normalized = cls._normalize_plaintext(plaintext)
        if iterations < cls.MIN_ITERATIONS:
            msg = f"Iterations must be at least {cls.MIN_ITERATIONS}."
            raise ValueError(msg)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            normalized.encode("utf-8"),
            urlsafe_b64decode(salt.encode("ascii")),
            iterations,
        )
        return urlsafe_b64encode(dk).decode("ascii")

    def set_password(self, plaintext: str) -> None:
        """Set salt and hash from plaintext for this record."""
        self.algorithm = self.DEFAULT_ALGORITHM
        self.salt = self.generate_salt()
        self.password_hash = self.derive_hash(plaintext, self.salt, self.iterations)

    def verify_password(self, plaintext: str) -> bool:
        """Verify plaintext against the stored hash in constant time."""
        expected = self.derive_hash(plaintext, self.salt, self.iterations)
        return hmac.compare_digest(expected, self.password_hash)

    def rotate_password(self, plaintext: str) -> None:
        """Replace the current hash and mark this record as active."""
        self.set_password(plaintext)
        self.is_active = True
        self.updated_at = datetime.now(UTC)

    def deactivate(self) -> None:
        """Mark this password record as inactive."""
        self.is_active = False

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return whether this password record has expired."""
        if self.expires_at is None:
            return False
        current = now or datetime.now(UTC)
        return self.expires_at <= current

    @classmethod
    def create_for_user(cls, user_id: int, plaintext: str, *, iterations: int | None = None) -> "Password":
        """Create a fully initialized password record for a user."""
        record = cls(
            user_id=user_id,
            iterations=iterations or cls.DEFAULT_ITERATIONS,
            salt="",
            password_hash="",
        )
        record.set_password(plaintext)
        return record
