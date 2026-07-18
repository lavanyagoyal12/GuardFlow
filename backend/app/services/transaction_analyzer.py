from __future__ import annotations

from typing import Any


class TransactionAnalyzer:
    """Extracts a simplified transaction-risk payload from payment-related events."""

    def analyze(self, events: list[Any] | None) -> dict[str, Any]:
        if not events:
            return {}

        latest_payment = None
        for event in reversed(events):
            payload = getattr(event, "payload", {}) or {}
            event_type = str(getattr(event, "event_type", "") or "").upper()
            if event_type in {"PAYMENT_STARTED", "PAYMENT_COMPLETED"}:
                latest_payment = {
                    "amount": payload.get("amount"),
                    "status": "completed" if event_type == "PAYMENT_COMPLETED" else "started",
                    "receiver": {"name": payload.get("receiver")},
                }
                break

        if not latest_payment:
            return {}

        return latest_payment
