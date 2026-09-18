"""Track a user's subscription plan and payment history."""
from __future__ import annotations

from enum import StrEnum

from herogold.orm.core.model import DataModel
from herogold.orm.core.utils import Relationship
from herogold.orm.models.user import User

from .subscription import BillingPlan


class PaymentStatus(StrEnum):
    """Payment status constants."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class PlanPayments(DataModel, table=True):
    """Track a user's subscription plan and payment history."""

    user = Relationship(User)
    plan = Relationship(BillingPlan)
    status: PaymentStatus

