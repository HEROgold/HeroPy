"""Association table for users and roles."""

from orm.core.model import BaseModel
from orm.core.utils import Relationship, get_foreign_key
from orm.models.role import Role
from orm.models.user import User
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, ForeignKey


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
