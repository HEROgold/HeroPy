"""Subscription plan model.

This contains the plan for a subscription.
It may or may not be in use, allows for custom pricing and duration of subscriptions.
It is used to define the subscription plan for a user.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import dinero.currencies as _currencies
from dinero.types import Currency

from herogold.orm.core.model import BaseModel


class BillingPlan(BaseModel, table=True):
    """Subscription plan model."""

    name: str
    price: Decimal
    # Stored as the ISO currency code (e.g. "USD"); dinero.types.Currency is a
    # TypedDict, not a column type, so the full dict is looked up on access
    # via `currency_info` instead of persisted directly.
    currency: str
    until: datetime

    @property
    def currency_info(self) -> Currency:
        """Resolve the stored currency code to its full dinero ``Currency`` dict."""
        try:
            return getattr(_currencies, self.currency.upper())
        except AttributeError as exc:
            msg = f"Unknown currency code: {self.currency!r}"
            raise ValueError(msg) from exc
