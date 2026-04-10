"""User configuration model."""

from orm.core.model import BaseModel
from orm.core.utils import Relationship, get_foreign_key
from orm.models.user import User
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, ForeignKey


class Configuration(BaseModel, table=True):
    """Store per-user key/value configuration settings."""

    __tablename__ = "configuration"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_configuration_user_key"),)

    user_id: int = Field(index=True, sa_column_args=(ForeignKey(get_foreign_key(User)),))
    user = Relationship(User)
    key: str = Field(index=True, nullable=False, max_length=120)
    value: str = Field(nullable=False)
    description: str | None = Field(default=None, max_length=255)
    is_secret: bool = Field(default=False)

    def set_value(self, value: str) -> None:
        """Update the stored configuration value."""
        self.value = value

    def as_pair(self) -> tuple[str, str]:
        """Return the key/value pair."""
        return (self.key, self.value)
