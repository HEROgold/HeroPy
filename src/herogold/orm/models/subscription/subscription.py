"""Subscription model."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from herogold.orm.core.model import BaseModel, DataModel
from herogold.orm.core.utils import Relationship
from herogold.orm.models.user import User

from .plan import BillingPlan


class SubscriptionStatus(StrEnum):
    """Subscription status constants."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PENDING = "pending"
    TRIALING = "trialing"

class Features(BaseModel, table=True):
    """Container for subscription features."""

    name: str
    value: str

class Subscription(DataModel, table=True):
    """Subscription model."""

    user = Relationship(User)
    status: SubscriptionStatus
    plan = Relationship(BillingPlan)
    features: Features

    def has_paid(self) -> bool:
        """Check if a subscription has been paid."""
        return self.payed_until() < datetime.now(tz=UTC)

    def payed_until(self) -> datetime:
        """Get the date until which the subscription has been paid."""
        # pyrefly does correctly infer the type of self.plan, ty doesn't.
        return self.plan.until  # ty: ignore[invalid-attribute-access]
