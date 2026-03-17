"""Association table for roles and permissions."""

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, ForeignKey

from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import Relationship, get_foreign_key
from herogold.orm.models.permission import Permission
from herogold.orm.models.role import Role


class RolePermission(BaseModel, table=True):
    """Map a role to a permission."""

    __tablename__ = "role_permission"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission_role_permission"),)

    role_id: int = Field(index=True, sa_column_args=(ForeignKey(get_foreign_key(Role)),))
    permission_id: int = Field(index=True, sa_column_args=(ForeignKey(get_foreign_key(Permission)),))
    role = Relationship(Role)
    permission = Relationship(Permission)

    def pair(self) -> tuple[int, int]:
        """Return the role and permission ids as a tuple."""
        return (self.role_id, self.permission_id)
