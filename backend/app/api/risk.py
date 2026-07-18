from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.database.database import get_db
from app.models.risk_assessment import RiskAssessment
from app.models.sessions import Session as SessionModel
from app.repositories.event_repository import EventRepository
from app.repositories.risk_repository import RiskRepository
from app.schemas.risk_schema import RiskResponse
from app.services.behaviour_analyzer import BehaviourAnalyzer
from app.services.llm_service import LLMService
from app.services.risk_engine import RiskEngine
from app.services.transaction_analyzer import TransactionAnalyzer
from app.services.warning_service import WarningService
from app.services.website_analyzer import WebsiteAnalyzer

# NOTE: no prefix here - main.py already mounts this router under "/api/v1".
# The previous version set prefix="/api/v1" on both this router AND on the
# include_router() call in main.py, which produced "/api/v1/api/v1/score/..."
router = APIRouter(
    tags=["Risk Assessment"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Resource not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Server error"},
    },
)

# Singletons: both are stateless/pure given a URL or numeric inputs, so one
# shared instance per process is safe and avoids re-instantiating per event.
_rule_engine = RiskEngine()
_website_analyzer = WebsiteAnalyzer()
_llm_service = LLMService()
_behaviour_analyzer = BehaviourAnalyzer()
_transaction_analyzer = TransactionAnalyzer()
_warning_service = WarningService()

# Per-event-type weight contributed toward the session's behaviour anomaly
# score. Keys must match real event_type values Android currently sends
# (verified against data/guardflow.db), normalized to upper-case since
# Android mixes casing ("WEBSITE_OPENED" vs "app_opened"/"link_clicked").
#
# "app_opened" is intentionally NOT weighted: in stored data it fires for
# benign OS components (keyboard, launcher, systemui), not curated
# security-relevant app switches. There is no package_name allowlist/
# blocklist anywhere in this codebase yet, so treating every app switch as
# anomalous would penalize normal phone use. See final-review notes.
#
# "WEBSITE_OPENED" is intentionally NOT weighted here: it already drives
# website_risk via WebsiteAnalyzer below and would double-count if also
# treated as a behavioural anomaly.
ANOMALY_WEIGHTS = {
    # Repeated link-follows within one session is a recognized
    # redirect-chain / link-hopping pattern used in phishing funnels -
    # the one repeatable behavioural signal Android currently reports.
    # "LINK_CLICKED": 5,
}


def _extract_page_analysis_risk(payload: dict, events=None) -> float:
    """Turn a stored PAGE_ANALYSIS event's payload into a 0-100 risk score."""
    url = payload.get("url")
    signals = payload.get("signals") or {}
    detector = signals.get("detector_findings") or {}

    deterministic_score = _extract_website_risk({"url": url}) if url else None
    score = deterministic_score if deterministic_score is not None else 0.0

    password_fields = signals.get("password_fields") or 0

    scam_keywords = detector.get("scam_keywords") if isinstance(detector.get("scam_keywords"), dict) else {}
    scam_keyword_count = int((scam_keywords.get("keyword_count") or 0)) if isinstance(scam_keywords.get("keyword_count"), (int, float)) else 0

    countdown_timers = detector.get("countdown_timers") if isinstance(detector.get("countdown_timers"), dict) else {}
    countdown_detected = bool(countdown_timers.get("detected")) if isinstance(countdown_timers.get("detected"), bool) else False

    registration_fee_requests = detector.get("registration_fee_requests")
    registration_fee_hits = registration_fee_requests or []
    if not isinstance(registration_fee_hits, list):
        registration_fee_hits = []

    if password_fields > 0 and scam_keyword_count > 0:
        score += 15
    if countdown_detected:
        score += 10
    if registration_fee_hits:
        score += 15

    llm_result = _llm_service.analyze_page(payload, events)
    '''llm_result = payload.get("llm_result")

    if llm_result is None:
        llm_result = _llm_service.analyze_page(payload, events)
        # Save it so we never compute it again
        payload["llm_result"] = llm_result'''

    llm_score = float(llm_result.get("website_score", 0) or 0)
    llm_confidence = int(llm_result.get("confidence", 0) or 0)
    llm_reasons = llm_result.get("reasons") or []
    llm_indicators = llm_result.get("indicators") or []
    score = max(score, llm_score)
    score = min(100.0, score)

    logger.info(
        "PAGE_ANALYSIS decision session={} url={} found={} llm_score={} llm_confidence={} fallback={}",
        payload.get("session_id") or "unknown",
        url,
        bool(payload),
        llm_score,
        llm_confidence,
        "llm" if llm_score else "deterministic",
    )
    logger.info(
        "PAGE_ANALYSIS evidence session={} reasons={} indicators={}",
        payload.get("session_id") or "unknown",
        llm_reasons,
        llm_indicators,
    )
    return score


def _extract_website_risk(payload: dict) -> float | None:
    """Lazily compute a website risk score from a WEBSITE_OPENED event's payload.

    WebsiteAnalyzer is deterministic, cheap, and (today) has no network
    dependency, so recomputing it on every /score call is preferable to
    persisting a value that could go stale once real reputation lookups
    are added later. Returns None if no usable URL is present or analysis
    fails, matching the previous "missing value" behaviour.

    Android's real payload key (verified against stored events) is "url" -
    no "link" fallback is used since that key has never been observed.
    """
    url = payload.get("url")
    if not url:
        return None
    try:
        return _website_analyzer.analyze(url).website_score
    except Exception as e:
        logger.warning(f"Website analysis failed for url={url!r}: {e}")
        return None


def _calculate_anomaly_score(events) -> int:
    """Sum configured anomaly weights across a session's stored events.

    Replaces the previous hardcoded `anomalies: 0` with a real, tunable
    tally derived entirely from event types already present in the DB.
    Capped at 100 to stay consistent with the 0-100 scale RiskEngine
    expects for every other sub-score.
    """
    total = 0
    for event in events:
        event_type = (event.event_type or "").upper()
        total += ANOMALY_WEIGHTS.get(event_type, 0)
    return min(100, total)


@router.post(
    "/score/{session_id}",
    response_model=RiskResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute (and persist) the risk assessment for a session",
    responses={
        status.HTTP_200_OK: {"description": "Risk assessment computed successfully"},
        status.HTTP_404_NOT_FOUND: {"description": "No events found for session"},
    },
)
def get_risk_score(
    session_id: str,
    db: Session = Depends(get_db),
) -> RiskResponse:
    """Compute a risk assessment for a session from its stored events.

    This is the ONLY place in the application that computes or persists a
    RiskAssessment. It pulls every event recorded for the session, analyzes
    website URLs, payment details, and behavioural anomalies, runs the
    result through the rule engine, persists exactly one RiskAssessment
    row, and returns the score.

    Args:
        session_id: ID of the session to assess
        db: Database session dependency

    Returns:
        RiskResponse: Freshly computed risk assessment data

    Raises:
        HTTPException: 404 if no events exist for this session
    """
    events = EventRepository(db).find_by_session(session_id)

    if not events:
        logger.warning(f"No events found for session {session_id}, cannot score")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No events found for this session",
        )

    website_risk = 0.0
    payment_data = {}
    receiver_data = {}
    latest_page_analysis = None
    for event in events:
        event_type = (event.event_type or "").upper()
        if event_type in {"WEBSITE_OPENED", "LINK_CLICKED"}:
            score = _extract_website_risk(event.payload or {})
            if score is not None:
                website_risk = max(website_risk, score)
        elif event_type == "PAGE_ANALYSIS":
            payload = event.payload or {}
            if payload:
                latest_page_analysis = payload
            score = _extract_page_analysis_risk(payload, events)
            if score is not None:
                website_risk = max(website_risk, score)
        elif event_type == "PAYMENT_STARTED":
            payment_data = {
                "amount": event.payload.get("amount"),
                "status": "started",
                "receiver": {"name": event.payload.get("receiver")},
            }
            receiver_data = payment_data["receiver"]
        elif event_type == "PAYMENT_COMPLETED":
            payment_data = {
                "amount": event.payload.get("amount"),
                "status": "completed",
                "receiver": {"name": event.payload.get("receiver")},
            }
            receiver_data = payment_data["receiver"]

    behaviour_data = _behaviour_analyzer.analyze(events)
    transaction_data = _transaction_analyzer.analyze(events)
    if transaction_data:
        payment_data = transaction_data
        receiver_data = transaction_data.get("receiver") or {}

    result = _rule_engine.calculate_risk(
        website_risk=website_risk,
        payment_risk_or_data=payment_data,
        receiver_risk_or_data=receiver_data,
        behaviour_risk_or_data=behaviour_data,
    )

    warning_decision = _warning_service.evaluate(result["overall_score"], result["risk_level"])
    result["warning_action"] = warning_decision["action"]
    result["warning_reason"] = warning_decision["reason"]

    # RiskAssessment.session_id is a FK to sessions.id, but nothing else in
    # the app ever inserts a Session row for the session_ids Android/the
    # extension generate - SQLite doesn't enforce FKs by default so this has
    # been silently working, but it's a landmine (breaks the moment FK
    # enforcement is turned on or the DB is swapped for one that enforces
    # it). Upsert a minimal row so the relationship is actually valid.
    if not db.get(SessionModel, session_id):
        db.merge(SessionModel(id=session_id))
        db.commit()

    assessment = RiskAssessment(
        session_id=session_id,
        score=result["overall_score"],
        level=result["risk_level"],
        confidence=result["confidence"],
        triggered_rules=result["reasons"],
        requires_physical_confirmation=result["requires_physical_confirmation"],
    )
    RiskRepository(db).save(assessment)

    logger.info(
        "Session scoring session_id={} page_analysis_found={} selected_url={} llm_score={} final_score={} level={}",
        session_id,
        bool(latest_page_analysis),
        (latest_page_analysis or {}).get("url") or "n/a",
        website_risk,
        result["overall_score"],
        result["risk_level"],
    )

    return RiskResponse(
        score=result["overall_score"],
        level=result["risk_level"],
        confidence=result["confidence"],
        triggered_rules=result["reasons"],
        requires_physical_confirmation=result["requires_physical_confirmation"],
    )
