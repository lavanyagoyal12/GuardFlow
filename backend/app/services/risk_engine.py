from typing import Optional, Dict, Any, List


class RiskEngine:
    """Aggregates structured sub-scores into a final overall risk score."""

    weight_website: float = 0.35
    weight_payment: float = 0.35
    weight_receiver: float = 0.20
    weight_behaviour: float = 0.10

    def _normalize_score(self, v: Optional[float]) -> float:
        if v is None:
            return 0.0
        try:
            return max(0.0, min(100.0, float(v)))
        except Exception:
            return 0.0

    def _score_from_payment(self, payment: Dict[str, Any]) -> float:
        if not payment:
            return 0.0
        amount = payment.get("amount") or 0
        status = (payment.get("status") or "").lower()
        receiver = payment.get("receiver") or {}
        if isinstance(receiver, dict):
            receiver_name = str(receiver.get("name") or "").strip().lower()
        else:
            receiver_name = str(receiver).strip().lower()

        score = 0.0
        try:
            score += min(100.0, float(amount) / 1000.0)
        except Exception:
            pass
        if status == "completed":
            score += 10.0
        if not receiver_name:
            score += 20.0
        return self._normalize_score(score)

    def _score_from_receiver(self, receiver_info: Dict[str, Any]) -> float:
        if not receiver_info:
            return 0.0
        name = str(receiver_info.get("name") or "").strip()
        return 70.0 if not name else 20.0

    def _score_from_behaviour(self, behaviour: Dict[str, Any]) -> float:
        if not behaviour:
            return 0.0
        anomalies = behaviour.get("anomalies", 0)
        return self._normalize_score(min(100.0, anomalies * 10))

    def calculate_risk(
        self,
        website_risk: Optional[float] = None,
        payment_risk_or_data: Optional[Any] = None,
        receiver_risk_or_data: Optional[Any] = None,
        behaviour_risk_or_data: Optional[Any] = None,
    ) -> Dict[str, Any]:
        website_score = self._normalize_score(website_risk)

        if isinstance(payment_risk_or_data, (int, float)):
            payment_score = self._normalize_score(payment_risk_or_data)
        else:
            payment_score = self._score_from_payment(payment_risk_or_data or {})

        if isinstance(receiver_risk_or_data, (int, float)):
            receiver_score = self._normalize_score(receiver_risk_or_data)
        else:
            receiver_score = self._score_from_receiver(receiver_risk_or_data or {})

        if isinstance(behaviour_risk_or_data, (int, float)):
            behaviour_score = self._normalize_score(behaviour_risk_or_data)
        else:
            behaviour_score = self._score_from_behaviour(behaviour_risk_or_data or {})

        overall = (
            website_score * self.weight_website
            + payment_score * self.weight_payment
            + receiver_score * self.weight_receiver
            + behaviour_score * self.weight_behaviour
        )
        overall = max(0.0, min(100.0, overall))

        if overall >= 60:
            level = "HIGH"
        elif overall >= 30:
            level = "MEDIUM"
        else:
            level = "LOW"

        present = sum(1 for v in (website_score, payment_score, receiver_score, behaviour_score) if v > 0)
        confidence = int(min(95, 50 + present * 10 + overall / 10))

        rules: List[Dict[str, Any]] = []
        if website_score > 50:
            rules.append({"rule_id": "website_high", "description": "Website analysis indicates concern", "weight": 35, "evidence": ["website_score"]})
        if payment_score > 50:
            rules.append({"rule_id": "payment_high", "description": "Payment details look suspicious", "weight": 35, "evidence": ["payment_score"]})
        if receiver_score > 50:
            rules.append({"rule_id": "receiver_high", "description": "Receiver information is incomplete or unknown", "weight": 20, "evidence": ["receiver_score"]})
        if behaviour_score > 50:
            rules.append({"rule_id": "behaviour_high", "description": "Unusual user behaviour observed", "weight": 10, "evidence": ["behaviour_score"]})

        return {
            "overall_score": int(round(overall)),
            "risk_level": level,
            "confidence": confidence,
            "reasons": [rule["description"] for rule in rules],
            "triggered_rules": rules,
            "requires_physical_confirmation": level == "HIGH",
        }
