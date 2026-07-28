from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace
import unittest

import httpx

from app.services.feature_extractor import FeatureExtractor
from app.services.llm_service import LLMService
from app.services.risk_engine import RiskEngine
from app.services.website_analyzer import WebsiteAnalyzer


def event(event_type, timestamp, payload=None):
    return SimpleNamespace(
        event_type=event_type,
        timestamp=timestamp,
        created_at=timestamp,
        payload=payload or {},
    )


def page_payload(*, suspicious=False):
    if not suspicious:
        return {
            "url": "https://www.flipkart.com/",
            "signals": {
                "url": "https://www.flipkart.com/",
                "domain": "www.flipkart.com",
                "summary": {"password_field_count": 0},
                "detector_findings": {
                    "url_analysis": {
                        "components": {"protocol": "https", "hostname": "www.flipkart.com"},
                        "observations": {
                            "url_length": 25,
                            "is_ip_address_url": False,
                            "is_punycode": False,
                            "has_suspicious_tld": False,
                        },
                    },
                    "scam_keywords": {
                        "matched_keywords": ["payment"],
                        "keyword_count": 1,
                        "total_keyword_occurences": 1,
                    },
                    "countdown_timers": {"detected": False},
                    "payment_signals": {
                        "amount_mentions": ["₹44,999"],
                        "upi_mentions": [],
                        "qr_payment_prompts": [],
                        "registration_fee_requests": [],
                    },
                    "qr_candidates": {"qr_present": False},
                    "government_references": [],
                    "form_field_classification": [],
                    "buttons": {"payment_buttons": []},
                    "link_analysis": {"summary": {}},
                },
            },
        }

    return {
        "url": "http://192.0.2.10/verify-account",
        "signals": {
            "url": "http://192.0.2.10/verify-account",
            "domain": "192.0.2.10",
            "summary": {"password_field_count": 1},
            "detector_findings": {
                "url_analysis": {
                    "components": {"protocol": "http", "hostname": "192.0.2.10"},
                    "observations": {
                        "url_length": 38,
                        "is_ip_address_url": True,
                        "is_punycode": False,
                        "has_suspicious_tld": False,
                    },
                },
                "scam_keywords": {
                    "matched_keywords": ["urgent", "verify", "prize"],
                    "keyword_count": 3,
                    "total_keyword_occurences": 8,
                },
                "countdown_timers": {"detected": True},
                "payment_signals": {
                    "amount_mentions": ["₹5,000"],
                    "upi_mentions": ["fraud@upi"],
                    "qr_payment_prompts": ["scan QR to pay"],
                    "registration_fee_requests": ["pay registration fee"],
                },
                "qr_candidates": {"qr_present": True},
                "government_references": ["government scheme"],
                "form_field_classification": [
                    {"has_sensitive_fields": True, "sensitive_field_count": 2}
                ],
                "buttons": {"payment_buttons": ["Pay now"]},
                "link_analysis": {"summary": {"textHrefMismatchCount": 2}},
            },
        },
    }


class RiskPipelineTests(unittest.TestCase):
    def setUp(self):
        self.extractor = FeatureExtractor()
        self.analyzer = WebsiteAnalyzer()
        self.engine = RiskEngine()
        self.now = datetime.now(timezone.utc)

    def score(self, payload, events=None):
        features = self.extractor.extract(payload, events or [])
        analysis = self.analyzer.analyze(features)
        return features, self.engine.calculate(features, analysis)

    def test_legitimate_commerce_page_is_low(self):
        _, result = self.score(page_payload())
        self.assertEqual(result["risk_level"], "LOW")
        self.assertLess(result["risk_score"], 30)
        self.assertEqual(result["triggered_rules"], [])

    def test_suspicious_page_and_payment_is_high(self):
        events = [
            event("LINK_CLICKED", self.now - timedelta(minutes=2), {"url": "http://192.0.2.10"}),
            event("PAYMENT_INITIATED", self.now - timedelta(minutes=1), {"amount": "₹5000"}),
            event("SCREEN_SHARE_STARTED", self.now),
        ]
        _, result = self.score(page_payload(suspicious=True), events)
        self.assertIn(result["risk_level"], {"HIGH", "CRITICAL"})
        self.assertGreaterEqual(result["risk_score"], 60)
        self.assertIn("correlation.registration_fee_payment", result["triggered_rules"])
        self.assertTrue(result["requires_physical_confirmation"])
        self.assertGreaterEqual(len(result["top_reasons"]), 1)
        self.assertLessEqual(len(result["top_reasons"]), 3)

    def test_missing_scheme_is_unknown_not_http(self):
        payload = page_payload()
        payload["url"] = "example.com/login"
        payload["signals"]["url"] = "example.com/login"
        payload["signals"]["detector_findings"]["url_analysis"] = {}
        features, result = self.score(payload)
        self.assertIsNone(features["url_features"]["https"])
        self.assertNotIn("url.explicit_http", result["triggered_rules"])

    def test_old_browsing_events_do_not_create_recent_behaviour_risk(self):
        old_events = [
            event("LINK_CLICKED", self.now - timedelta(hours=1, seconds=index), {"url": f"https://safe{index}.test"})
            for index in range(20)
        ]
        recent = event("LINK_CLICKED", self.now, {"url": "https://current.test"})
        features, result = self.score(page_payload(), old_events + [recent])
        self.assertEqual(features["behaviour_features"]["rapid_link_count"], 1)
        self.assertNotIn("behaviour.rapid_linking", result["triggered_rules"])

    def test_android_payment_names_are_supported_and_states_are_not_double_counted(self):
        events = [
            event("PAYMENT_INITIATED", self.now - timedelta(seconds=10), {"amount": 7000, "receiver": "merchant@upi"}),
            event("PAYMENT_CONFIRMED", self.now, {}),
        ]
        features, _ = self.score(page_payload(), events)
        transaction = features["transaction_features"]
        self.assertTrue(transaction["payment_started"])
        self.assertTrue(transaction["payment_confirmed"])
        self.assertEqual(transaction["attempt_count"], 1)
        self.assertEqual(transaction["receiver"], "merchant@upi")

    def test_android_url_is_used_while_page_analysis_is_pending(self):
        events = [
            event("LINK_CLICKED", self.now, {"url": "https://pending.example/path"})
        ]
        features, result = self.score(None, events)
        self.assertEqual(features["url_features"]["url"], "https://pending.example/path")
        self.assertTrue(features["availability"]["url_features"])
        self.assertFalse(features["availability"]["website_content"])
        self.assertEqual(result["risk_level"], "LOW")

    def test_geniex_semantics_are_validated_and_model_score_is_discarded(self):
        def handler(request: httpx.Request) -> httpx.Response:
            request_body = json.loads(request.content)
            self.assertTrue(str(request.url).endswith("/v1/chat/completions"))
            self.assertEqual(request_body["temperature"], 0)
            self.assertNotIn("risk_score", request_body)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "phishing_intent": True,
                                        "fake_branding": False,
                                        "urgency_language": True,
                                        "social_engineering": True,
                                        "trustworthiness": "suspicious",
                                        "evidence": ["Urgent verification language is present"],
                                        "risk_score": 100,
                                    }
                                )
                            }
                        }
                    ]
                },
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        service = LLMService(enabled=True, client=client)
        result = service.analyze_semantics({"page": {"title": "Verify now"}})

        self.assertTrue(result["available"])
        self.assertTrue(result["phishing_intent"])
        self.assertNotIn("risk_score", result)

    def test_invalid_llm_json_falls_back_without_changing_baseline(self):
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"choices": [{"message": {"content": '{"phishing_intent":"yes"}'}}]},
                )
            )
        )
        semantic = LLMService(enabled=True, client=client).analyze_semantics(
            {"page": {"title": "Example"}}
        )
        self.assertFalse(semantic["available"])

        features = self.extractor.extract(page_payload(), [])
        without_llm = self.engine.calculate(features, self.analyzer.analyze(features))
        with_fallback = self.engine.calculate(
            features,
            self.analyzer.analyze(features, semantic),
        )
        self.assertEqual(without_llm["risk_score"], with_fallback["risk_score"])

    def test_semantic_scoring_is_fixed_and_capped_by_risk_engine(self):
        features = self.extractor.extract(page_payload(), [])
        semantic = {
            "available": True,
            "phishing_intent": True,
            "fake_branding": True,
            "urgency_language": True,
            "social_engineering": True,
            "trustworthiness": "suspicious",
            "evidence": ["Model evidence"],
            # This invented score must have no effect.
            "risk_score": 100,
        }
        result = self.engine.calculate(
            features,
            self.analyzer.analyze(features, semantic),
        )
        self.assertEqual(
            result["semantic_content_points"],
            self.engine.MAX_SEMANTIC_CONTENT_POINTS,
        )
        self.assertLess(result["risk_score"], 30)

    def test_llm_explainer_uses_only_level_reasons_and_recommendation(self):
        def handler(request: httpx.Request) -> httpx.Response:
            request_body = json.loads(request.content)
            user_content = request_body["messages"][1]["content"]
            self.assertNotIn("risk_score", user_content)
            self.assertNotIn("confidence", user_content)
            self.assertIn("reasons", user_content)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    "This session is high risk because the page requests "
                                    "credentials and uses urgent payment language. Stop the "
                                    "payment and verify the website independently."
                                )
                            }
                        }
                    ]
                },
            )

        result = LLMService(
            enabled=True,
            client=httpx.Client(transport=httpx.MockTransport(handler)),
        ).explain_result(
            {
                "risk_score": 78,
                "risk_level": "HIGH",
                "top_reasons": [
                    "Sensitive credential fields were detected",
                    "Countdown or urgency language was detected",
                    "A payment request was detected on the page",
                ],
                "recommendations": [
                    "Pause the payment and verify the website independently"
                ],
            }
        )

        self.assertTrue(result["available"])
        self.assertIn("high risk", result["explanation"].lower())

    def test_llm_explainer_has_a_human_fallback_for_every_level(self):
        service = LLMService(enabled=False)
        for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            result = service.explain_result(
                {
                    "risk_level": level,
                    "top_reasons": (
                        [] if level == "LOW" else ["Sensitive fields were detected"]
                    ),
                    "recommendations": ["Verify the website before continuing"],
                }
            )
            self.assertFalse(result["available"])
            self.assertTrue(result["explanation"])
            self.assertLessEqual(len(result["explanation"]), 600)


if __name__ == "__main__":
    unittest.main()
