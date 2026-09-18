"""Subscription model."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from herogold.orm.core.model import BaseModel, DataModel

if TYPE_CHECKING:

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

    user: User
    status: SubscriptionStatus
    plan: BillingPlan
    features: Features

    def has_paid(self) -> bool:
        """Check if a subscription has been paid."""
        return self.payed_until() < datetime.now(tz=UTC)

    def payed_until(self) -> datetime:
        """Get the date until which the subscription has been paid."""
        return self.plan.until
