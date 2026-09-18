"""Tests for the subscription/billing models.

Focused on business pitfalls a subscription system is prone to: expiry
boundaries, timezone handling, currency precision, dangling/unset
relationships, and whether the "audit history" DataModel actually keeps
history.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlmodel import select

from herogold.orm.models.subscription.payments import PaymentStatus, PlanPayments
from herogold.orm.models.subscription.plan import BillingPlan
from herogold.orm.models.subscription.subscription import Features, Subscription, SubscriptionStatus
from herogold.orm.models.user import User

if TYPE_CHECKING:
    from sqlmodel import Session


def _make_plan(session: Session, *, until: datetime, currency: str = "USD", price: Decimal = Decimal("9.99")) -> BillingPlan:
    plan = BillingPlan(name="pro", price=price, currency=currency, until=until)
    plan.add(session)
    return plan


def _make_user(session: Session, username: str = "alice") -> User:
    user = User(username=username)
    user.add(session)
    return user


def _make_subscription(session: Session, status: SubscriptionStatus = SubscriptionStatus.ACTIVE) -> Subscription:
    sub = Subscription(status=status)
    sub.add(session)
    return sub


# --- BillingPlan --------------------------------------------------------


def test_billing_plan_currency_info_resolves_code(session: Session) -> None:
    plan = _make_plan(session, until=datetime.now(UTC) + timedelta(days=30), currency="USD")

    assert plan.currency_info == {"code": "USD", "base": 10, "exponent": 2}


def test_billing_plan_currency_info_is_case_insensitive(session: Session) -> None:
    plan = _make_plan(session, until=datetime.now(UTC) + timedelta(days=30), currency="usd")

    assert plan.currency_info["code"] == "USD"


def test_billing_plan_unknown_currency_raises(session: Session) -> None:
    plan = _make_plan(session, until=datetime.now(UTC) + timedelta(days=30), currency="NOTACURRENCY")

    with pytest.raises(ValueError, match="Unknown currency code"):
        plan.currency_info  # noqa: B018


def test_billing_plan_price_keeps_decimal_precision(session: Session) -> None:
    # A classic billing pitfall: prices silently rounded/represented as float
    # (e.g. Decimal("19.99") becoming 19.990000000000002) corrupt invoices.
    plan = _make_plan(session, until=datetime.now(UTC) + timedelta(days=30), price=Decimal("19.99"))

    reloaded = BillingPlan.get(plan.id, session=session)

    assert reloaded.price == Decimal("19.99")
    assert isinstance(reloaded.price, Decimal)


# --- Subscription.has_paid / payed_until --------------------------------


def test_has_paid_true_while_plan_is_active(session: Session) -> None:
    plan = _make_plan(session, until=datetime.now(UTC) + timedelta(days=30))
    sub = _make_subscription(session)
    sub.plan = plan

    assert sub.has_paid() is True


def test_has_paid_false_once_plan_has_expired(session: Session) -> None:
    # The plan's paid-until date is in the past: the subscription must read
    # as unpaid. (Regression guard: has_paid() previously had this inverted.)
    plan = _make_plan(session, until=datetime.now(UTC) - timedelta(days=1))
    sub = _make_subscription(session)
    sub.plan = plan

    assert sub.has_paid() is False


def test_payed_until_normalizes_naive_datetime_to_utc(session: Session) -> None:
    # Some backends (SQLite included) drop tzinfo on round-trip. A naive
    # "until" must not blow up has_paid()'s comparison against an aware "now".
    plan = _make_plan(session, until=datetime.now(UTC) + timedelta(days=30))
    plan.until = plan.until.replace(tzinfo=None)  # simulate a naive value from the DB
    sub = _make_subscription(session)
    sub.plan = plan

    assert sub.payed_until().tzinfo is not None
    assert sub.has_paid() is True


def test_has_paid_without_a_plan_raises_instead_of_silently_passing(session: Session) -> None:
    # Pitfall: a Subscription created without ever attaching a BillingPlan
    # (e.g. a signup flow that errors out before the plan step) must not be
    # silently treated as paid or unpaid -- it should fail loudly.
    sub = _make_subscription(session)

    with pytest.raises(AttributeError):
        sub.has_paid()


def test_reassigning_plan_replaces_previous_link(session: Session) -> None:
    # Business pitfall: upgrading/downgrading a plan must not leave the
    # subscription pointing at (or additionally linked to) the old plan.
    old_plan = _make_plan(session, until=datetime.now(UTC) + timedelta(days=1))
    new_plan = _make_plan(session, until=datetime.now(UTC) + timedelta(days=30))
    sub = _make_subscription(session)

    sub.plan = old_plan
    sub.plan = new_plan

    assert sub.plan is not None
    assert sub.plan.id == new_plan.id


# --- Relationships (user / features) ------------------------------------


def test_subscription_user_relationship_round_trips(session: Session) -> None:
    user = _make_user(session)
    sub = _make_subscription(session)

    sub.user = user

    assert sub.user is not None
    assert sub.user.id == user.id


def test_subscription_without_user_returns_none_not_error(session: Session) -> None:
    sub = _make_subscription(session)

    assert sub.user is None


def test_subscription_features_relationship_round_trips(session: Session) -> None:
    features = Features(name="seats", value="10")
    features.add(session)
    sub = _make_subscription(session)

    sub.features = features

    assert sub.features is not None
    assert sub.features.value == "10"


# --- Status enums ---------------------------------------------------------


def test_subscription_status_is_not_actually_validated(session: Session) -> None:
    # Pitfall: SQLModel table=True models skip enum-membership validation on
    # construction, so any string is silently accepted as a `status` instead
    # of raising. A typo'd status (e.g. from a config file or API payload)
    # will pass straight through and can produce a Subscription that no
    # branch of business logic recognizes as active, paid, or canceled.
    sub = Subscription(status="not-a-real-status")  # type: ignore[arg-type]

    assert sub.status == "not-a-real-status"
    assert not isinstance(sub.status, SubscriptionStatus)


def test_payment_status_is_not_actually_validated(session: Session) -> None:
    payment = PlanPayments(status="not-a-real-status")  # type: ignore[arg-type]

    assert payment.status == "not-a-real-status"
    assert not isinstance(payment.status, PaymentStatus)


def test_plan_payments_tracks_user_and_plan(session: Session) -> None:
    user = _make_user(session)
    plan = _make_plan(session, until=datetime.now(UTC) + timedelta(days=30))
    payment = PlanPayments(status=PaymentStatus.COMPLETED)
    payment.add(session)

    payment.user = user
    payment.plan = plan

    assert payment.user is not None
    assert payment.user.id == user.id
    assert payment.plan is not None
    assert payment.plan.id == plan.id
    assert payment.status is PaymentStatus.COMPLETED


def test_failed_payment_does_not_implicitly_change_subscription_status(session: Session) -> None:
    # Pitfall: a failed payment record existing does not, by itself, cancel
    # or otherwise change an already-active subscription. Nothing wires the
    # two together automatically, so a caller must not assume it does.
    plan = _make_plan(session, until=datetime.now(UTC) + timedelta(days=30))
    sub = _make_subscription(session, status=SubscriptionStatus.ACTIVE)
    sub.plan = plan
    payment = PlanPayments(status=PaymentStatus.FAILED)
    payment.add(session)
    payment.plan = plan

    assert sub.status is SubscriptionStatus.ACTIVE
    assert sub.has_paid() is True


# --- DataModel history/audit-trail behavior ------------------------------


def test_update_does_not_preserve_prior_history_row(session: Session) -> None:
    # DataModel is documented as "Base model for models that require a
    # history of changes" via its composite (id, timestamp) primary key --
    # implying every update should leave the old row in place and insert a
    # new timestamped one. It does not: `.update()` reuses the same
    # `timestamp` the instance already had (default_factory only runs once,
    # at construction) and overwrites the existing row in place. For a
    # subscription this means canceling/renewing loses the prior status
    # instead of keeping an auditable history -- a real pitfall for billing
    # disputes. This test pins down the *current* behavior so a future fix
    # is a deliberate, visible change rather than a silent regression.
    sub = _make_subscription(session, status=SubscriptionStatus.ACTIVE)
    original_timestamp = sub.timestamp

    sub.status = SubscriptionStatus.CANCELED
    sub.update(session)

    rows = session.exec(select(Subscription).where(Subscription.id == sub.id)).all()
    assert len(rows) == 1
    assert rows[0].timestamp == original_timestamp
    assert rows[0].status is SubscriptionStatus.CANCELED
