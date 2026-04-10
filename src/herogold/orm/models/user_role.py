"""Association table for users and roles."""

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, ForeignKey

from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import Relationship, get_foreign_key
from herogold.orm.models.role import Role
from herogold.orm.models.user import User


class UserRole(BaseModel, table=True):
    """Map users to roles."""

    __tablename__ = "user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role_user_role"),)

    user_id: int = Field(index=True, sa_column_args=(ForeignKey(get_foreign_key(User)),))
    role_id: int = Field(index=True, sa_column_args=(ForeignKey(get_foreign_key(Role)),))
    user = Relationship(User)
    role = Relationship(Role)

    def pair(self) -> tuple[int, int]:
        """Return the user and role ids as a tuple."""
        return (self.user_id, self.role_id)
