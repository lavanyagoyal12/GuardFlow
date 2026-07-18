from __future__ import annotations

import json
from typing import Any, Iterable


class PromptBuilder:
    """Builds a compact prompt from useful PAGE_ANALYSIS signals only."""

    def build_prompt(self, page_analysis: dict[str, Any] | None, events: Iterable[Any] | None = None) -> str:
        if not page_analysis:
            return (
                "You are a fraud-risk analyst. No page analysis payload was provided. "
                "Return valid JSON with website_score 0, confidence 20, reasons ['No page analysis available'], and indicators []."
            )

        signals = (page_analysis.get("signals") or {}) if isinstance(page_analysis, dict) else {}
        summary = signals.get("summary") or {}
        detector = signals.get("detector_findings") or {}
        forms = signals.get("forms") or {}
        sensitive_fields = signals.get("sensitive_fields") or {}
        payment_signals = signals.get("payment_signals") or {}
        qr = signals.get("qr") or {}
        countdown = signals.get("countdown") or {}
        urgency = signals.get("urgency") or {}
        metadata = signals.get("metadata") or {}
        url_analysis = signals.get("url_analysis") or {}

        compact_payload = {
            "url": page_analysis.get("url"),
            "summary": summary,
            "detector_findings": detector,
            "forms": forms,
            "sensitive_fields": sensitive_fields,
            "payment_signals": payment_signals,
            "qr": qr,
            "countdown": countdown,
            "urgency": urgency,
            "metadata": metadata,
            "url_analysis": url_analysis,
        }

        payload_json = json.dumps(compact_payload, ensure_ascii=False, sort_keys=True)
        event_context = []
        if events is not None:
            for event in events:
                event_context.append(
                    {
                        "event_type": getattr(event, "event_type", None),
                        "source_app": getattr(event, "source_app", None),
                    }
                )

        event_context_json = json.dumps(event_context[-6:], ensure_ascii=False)
        return (
            "You are evaluating a web page for fraud risk. Return ONLY valid JSON with keys "
            "website_score, confidence, reasons, and indicators. "
            "website_score must be an integer from 0 to 100. "
            "confidence must be an integer from 0 to 100. "
            "reasons must be an array of short strings. "
            "indicators must be an array of short strings.\n"
            f"Page signals: {payload_json}\n"
            f"Recent session context: {event_context_json}\n"
            "Use only the provided signals. Prefer conservative scores when evidence is weak."
        )
