"""Permission model."""

from sqlmodel import Field

from herogold.orm.core.model import BaseModel


class Permission(BaseModel, table=True):
    """Store a permission that can be assigned to users or roles."""

    __tablename__ = "permission"

    name: str = Field(index=True, unique=True, nullable=False, max_length=150)
    resource: str = Field(index=True, nullable=False, max_length=80)
    action: str = Field(index=True, nullable=False, max_length=80)
    description: str | None = Field(default=None, max_length=255)

    @staticmethod
    def build_name(resource: str, action: str) -> str:
        """Build a canonical permission name."""
        normalized_resource = resource.strip().lower()
        normalized_action = action.strip().lower()
        if not normalized_resource or not normalized_action:
            msg = "Resource and action are required."
            raise ValueError(msg)
        return f"{normalized_resource}:{normalized_action}"

    def set_from_parts(self, resource: str, action: str, description: str | None = None) -> None:
        """Populate fields from resource/action components."""
        self.resource = resource.strip().lower()
        self.action = action.strip().lower()
        self.name = self.build_name(resource, action)
        self.description = description
