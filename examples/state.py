"""Example taken from https://github.com/ArjanCodes/examples/blob/main/2026/state/final.py"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from herogold.state import StateMachine


class PayState(Enum):
    """States for payment processing."""

    NEW = auto()
    AUTHORIZED = auto()
    CAPTURED = auto()
    FAILED = auto()
    REFUNDED = auto()


class PayEvent(Enum):
    """Events for payment processing."""

    AUTHORIZE = auto()
    CAPTURE = auto()
    FAIL = auto()
    REFUND = auto()


@dataclass
class PaymentCtx:
    """Context for payment processing."""

    payment_id: str
    audit: list[str] = field(default_factory=list[str])


# Create an instance: this is "the machine"
pay_sm = StateMachine[PayState, PayEvent, PaymentCtx]()


@pay_sm.add(PayState.NEW, PayEvent.AUTHORIZE, PayState.AUTHORIZED)
def authorize(ctx: PaymentCtx) -> None:
    ctx.audit.append(f"{ctx.payment_id}: authorized")


@pay_sm.add((PayState.NEW, PayState.AUTHORIZED), PayEvent.FAIL, PayState.FAILED)
def fail(ctx: PaymentCtx) -> None:
    ctx.audit.append(f"{ctx.payment_id}: failed")


@pay_sm.add(PayState.AUTHORIZED, PayEvent.CAPTURE, PayState.CAPTURED)
def capture(ctx: PaymentCtx) -> None:
    ctx.audit.append(f"{ctx.payment_id}: captured")


@pay_sm.add(
    (PayState.AUTHORIZED, PayState.CAPTURED),
    PayEvent.REFUND,
    PayState.REFUNDED,
)
def refund(ctx: PaymentCtx) -> None:
    ctx.audit.append(f"{ctx.payment_id}: refunded")


@dataclass
class Payment:
    ctx: PaymentCtx
    state: PayState = PayState.NEW

    def handle(self, event: PayEvent) -> None:
        self.state = pay_sm.handle(self.ctx, self.state, event)


def main() -> None:
    p = Payment(ctx=PaymentCtx("p1"))

    p.handle(PayEvent.AUTHORIZE)
    p.handle(PayEvent.CAPTURE)
    p.handle(PayEvent.REFUND)

    print("state:", p.state)
    print("audit:", p.ctx.audit)

    # Uncomment to see an invalid transition:
    p2 = Payment(ctx=PaymentCtx("p2", []))
    p2.handle(PayEvent.CAPTURE)


if __name__ == "__main__":
    main()
