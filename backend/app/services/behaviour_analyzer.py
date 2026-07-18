from __future__ import annotations

from typing import Any


class BehaviourAnalyzer:
    """Turns session behaviour events into a compact behaviour-risk summary."""

    def analyze(self, events: list[Any] | None) -> dict[str, Any]:
        if not events:
            return {"anomalies": 0, "event_count": 0}

        event_count = len(events)
        anomalies = 0
        for event in events:
            event_type = str(getattr(event, "event_type", "") or "").upper()
            if event_type in {"LINK_CLICKED", "WEBSITE_OPENED"}:
                anomalies += 1
            elif event_type in {"PAYMENT_STARTED", "PAYMENT_COMPLETED"}:
                anomalies += 2

        return {"anomalies": min(100, anomalies), "event_count": event_count}
