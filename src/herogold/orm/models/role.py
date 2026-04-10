"""Role model."""

from orm.core.model import BaseModel
from sqlmodel import Field


class Role(BaseModel, table=True):
    """Store a role that groups permissions."""

    __tablename__ = "role"

    name: str = Field(index=True, unique=True, nullable=False, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    is_system: bool = Field(default=False, index=True)

    @staticmethod
    def normalize_name(value: str) -> str:
        """Normalize role names for consistency."""
        return value.strip().lower().replace(" ", "_")

    def set_name(self, value: str) -> None:
        """Set role name with normalization and validation."""
        normalized = self.normalize_name(value)
        if not normalized:
            msg = "Role name cannot be empty."
            raise ValueError(msg)
        self.name = normalized
