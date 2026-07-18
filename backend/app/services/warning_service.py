from __future__ import annotations

from typing import Any


class WarningService:
    """Determines whether a session should be warned or blocked based on the final score."""

    def evaluate(self, score: int, level: str | None = None) -> dict[str, Any]:
        normalized_level = (level or "LOW").upper()
        if score >= 80 or normalized_level == "HIGH":
            return {"action": "BLOCK", "reason": "High fraud risk detected"}
        if score >= 50 or normalized_level == "MEDIUM":
            return {"action": "WARN", "reason": "Moderate fraud risk detected"}
        return {"action": "ALLOW", "reason": "No action required"}
