"""Association table for users and secondary emails."""

from orm.core.model import BaseModel
from orm.core.utils import Relationship, get_foreign_key
from orm.models.email import Email
from orm.models.user import User
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, ForeignKey


class UserEmail(BaseModel, table=True):
    """Map users to their secondary email addresses."""

    __tablename__ = "user_email"
    __table_args__ = (UniqueConstraint("user_id", "email_id", name="uq_user_email_user_email"),)

    user_id: int = Field(index=True, sa_column_args=(ForeignKey(get_foreign_key(User)),))
    email_id: int = Field(index=True, sa_column_args=(ForeignKey(get_foreign_key(Email)),))
    user = Relationship(User)
    email = Relationship(Email)

    def pair(self) -> tuple[int, int]:
        """Return the user and email ids as a tuple."""
        return (self.user_id, self.email_id)
