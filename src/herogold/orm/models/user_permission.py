"""Association table for users and direct permissions."""

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, ForeignKey

from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import Relationship, get_foreign_key
from herogold.orm.models.permission import Permission
from herogold.orm.models.user import User


class UserPermission(BaseModel, table=True):
    """Map users to directly granted permissions."""

    __tablename__ = "user_permission"
    __table_args__ = (UniqueConstraint("user_id", "permission_id", name="uq_user_permission_user_permission"),)

    user_id: int = Field(index=True, sa_column_args=(ForeignKey(get_foreign_key(User)),))
    permission_id: int = Field(index=True, sa_column_args=(ForeignKey(get_foreign_key(Permission)),))
    user = Relationship(User)
    permission = Relationship(Permission)

    def pair(self) -> tuple[int, int]:
        """Return the user and permission ids as a tuple."""
        return (self.user_id, self.permission_id)
