"""Track a user's subscription plan and payment history."""
from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from herogold.orm.core.model import DataModel

if TYPE_CHECKING:

    from herogold.orm.models.user import User

    from .subscription import BillingPlan

class PaymentStatus(StrEnum):
    """Payment status constants."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"

class PlanPayments(DataModel, table=True):
    """Track a user's subscription plan and payment history."""

    user: User
    plan: BillingPlan
    status: PaymentStatus

