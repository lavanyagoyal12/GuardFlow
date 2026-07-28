"""Deterministic interpretation of normalized website observations."""

from __future__ import annotations

from typing import Any


class WebsiteAnalyzer:
    """Combine objective observations and validated LLM semantics without scoring."""

    def analyze(
        self,
        features: dict[str, Any],
        semantic_analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = features.get("url_features") or {}
        content = features.get("content_features") or {}

        suspicious_url = any(
            (
                url.get("is_ip_address"),
                url.get("is_punycode"),
                url.get("suspicious_tld"),
                url.get("excessive_hyphens"),
                url.get("is_shortener"),
                (url.get("url_length") or 0) >= 100,
            )
        )
        credential_collection = any(
            (
                (content.get("sensitive_form_count") or 0) > 0,
                (content.get("sensitive_field_count") or 0) > 0,
                (content.get("password_field_count") or 0) > 0,
            )
        )
        payment_request = any(
            (
                content.get("registration_fee_detected"),
                content.get("upi_detected"),
                content.get("qr_payment_prompt"),
                (content.get("payment_button_count") or 0) > 0,
            )
        )
        urgency = bool(content.get("countdown_detected"))
        government_claim = (content.get("government_reference_count") or 0) > 0
        keyword_cluster = (
            (content.get("scam_keyword_count") or 0) >= 3
            or (content.get("scam_keyword_occurrences") or 0) >= 5
        )
        qr_payment_request = bool(
            content.get("qr_present")
            and (content.get("qr_payment_prompt") or content.get("upi_detected"))
        )
        suspicious_links = any(
            (
                (content.get("shortened_link_count") or 0) > 0,
                (content.get("suspicious_domain_count") or 0) > 0,
                (content.get("text_href_mismatch_count") or 0) > 0,
            )
        )
        social_engineering = any(
            (
                urgency and payment_request,
                government_claim and credential_collection,
                content.get("registration_fee_detected") and keyword_cluster,
            )
        )

        observations = {
            "explicit_http": url.get("https") is False,
            "suspicious_url_structure": suspicious_url,
            "credential_collection": credential_collection,
            "payment_request": payment_request,
            "registration_fee_request": bool(content.get("registration_fee_detected")),
            "urgency_language": urgency,
            "government_reference": government_claim,
            "qr_payment_request": qr_payment_request,
            "high_risk_keyword_cluster": keyword_cluster,
            "suspicious_link_pattern": suspicious_links,
            "social_engineering_pattern": social_engineering,
        }

        semantic = self._semantic_result(semantic_analysis)
        semantic_evidence = (
            [f"Semantic analysis: {item}" for item in semantic["evidence"]]
            if semantic["available"]
            else []
        )

        return {
            "observations": observations,
            "semantic_analysis": semantic,
            "evidence": self._build_evidence(url, content, observations) + semantic_evidence,
        }

    def compact_llm_evidence(self, features: dict[str, Any]) -> dict[str, Any]:
        """Build the only website evidence that may be sent to the local LLM."""
        url = features.get("url_features") or {}
        content = features.get("content_features") or {}
        return {
            "url": {
                "value": url.get("url"),
                "domain": url.get("domain"),
                "https": url.get("https"),
                "is_ip_address": bool(url.get("is_ip_address")),
                "is_punycode": bool(url.get("is_punycode")),
                "suspicious_tld": bool(url.get("suspicious_tld")),
                "is_shortener": bool(url.get("is_shortener")),
            },
            "page": {
                "title": content.get("page_title"),
                "description": content.get("page_description"),
                "visible_text_excerpt": content.get("visible_text_excerpt"),
            },
            "detectors": {
                "matched_keywords": list(content.get("matched_keywords") or [])[:10],
                "scam_keyword_count": content.get("scam_keyword_count", 0),
                "scam_keyword_occurrences": content.get("scam_keyword_occurrences", 0),
                "countdown_detected": bool(content.get("countdown_detected")),
                "registration_fee_samples": list(content.get("registration_fee_samples") or [])[:3],
                "upi_detected": bool(content.get("upi_detected")),
                "qr_present": bool(content.get("qr_present")),
                "qr_payment_samples": list(content.get("qr_payment_samples") or [])[:3],
                "government_reference_samples": list(
                    content.get("government_reference_samples") or []
                )[:3],
                "sensitive_form_count": content.get("sensitive_form_count", 0),
                "sensitive_field_count": content.get("sensitive_field_count", 0),
                "password_field_count": content.get("password_field_count", 0),
                "payment_button_samples": list(content.get("payment_button_samples") or [])[:3],
            },
        }

    @staticmethod
    def _semantic_result(value: dict[str, Any] | None) -> dict[str, Any]:
        supplied = value if isinstance(value, dict) else {}
        available = supplied.get("available") is True
        return {
            "available": available,
            "phishing_intent": available and supplied.get("phishing_intent") is True,
            "fake_branding": available and supplied.get("fake_branding") is True,
            "urgency_language": available and supplied.get("urgency_language") is True,
            "social_engineering": available and supplied.get("social_engineering") is True,
            "trustworthiness": (
                supplied.get("trustworthiness")
                if available
                and supplied.get("trustworthiness") in {"trusted", "suspicious", "unknown"}
                else "unknown"
            ),
            "evidence": [
                str(item).strip()[:240]
                for item in list(supplied.get("evidence") or [])[:6]
                if str(item).strip()
            ] if available else [],
            "fallback_reason": supplied.get("fallback_reason") if not available else None,
        }

    def _build_evidence(
        self,
        url: dict[str, Any],
        content: dict[str, Any],
        observations: dict[str, bool],
    ) -> list[str]:
        evidence: list[str] = []

        if observations["explicit_http"]:
            evidence.append("The analyzed page explicitly uses HTTP instead of HTTPS")
        if url.get("is_ip_address"):
            evidence.append("The URL uses a raw IP address")
        if url.get("is_punycode"):
            evidence.append("The hostname contains punycode")
        if url.get("suspicious_tld"):
            evidence.append("The URL uses a watched high-abuse TLD")
        if content.get("registration_fee_detected"):
            evidence.append("Registration-fee language was detected")
        if content.get("upi_detected"):
            evidence.append("UPI payment language or an identifier was detected")
        if observations["qr_payment_request"]:
            evidence.append("QR evidence appears together with payment language")
        if observations["credential_collection"]:
            evidence.append("The page requests sensitive or credential-related fields")
        if observations["urgency_language"]:
            evidence.append("Countdown or urgency language was detected")
        if observations["government_reference"]:
            evidence.append("Government-related references were detected")
        if observations["suspicious_link_pattern"]:
            evidence.append("Suspicious link characteristics were detected")

        matched = [str(item) for item in content.get("matched_keywords", []) if item]
        if matched:
            evidence.append(f"Matched page keywords: {', '.join(matched[:5])}")

        return evidence[:12]
