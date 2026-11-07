from __future__ import annotations

from datetime import UTC, datetime

from herogold.orm.models.email import Email


def test_email_mark_verified_stores_given_timestamp() -> None:
    email = Email(email="user@example.com")
    stamp = datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)

    email.mark_verified(stamp)

    assert email.is_verified
    assert email.verified_at == stamp


def test_email_mark_verified_defaults_to_current_utc_time() -> None:
    email = Email(email="user@example.com")
    before = datetime.now(UTC)

    email.mark_verified()

    assert email.is_verified
    assert email.verified_at is not None
    assert email.verified_at.tzinfo is not None
    assert before <= email.verified_at <= datetime.now(UTC)
