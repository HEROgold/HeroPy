"""Subscription plan model.

This contains the plan for a subscription.
It may or may not be in use, allows for custom pricing and duration of subscriptions.
It is used to define the subscription plan for a user.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from herogold.orm.core.model import BaseModel

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

    from dinero.types import Currency


class BillingPlan(BaseModel, table=True):
    """Subscription plan model."""

    name: str
    price: Decimal
    currency: Currency
    until: datetime
