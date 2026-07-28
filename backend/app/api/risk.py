"""Risk-scoring API orchestration.

This route preserves the Android/API response contract. It selects the latest
stored extension analysis, extracts deterministic features once, calculates
the final score, adds a fail-safe human explanation, and persists the
assessment. The LLM never calculates or changes the score.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.database.database import get_db
from app.models.risk_assessment import RiskAssessment
from app.models.sessions import Session as SessionModel
from app.repositories.event_repository import EventRepository
from app.repositories.risk_repository import RiskRepository
from app.schemas.risk_schema import (
    RiskResponse,
    LatestRiskAssessmentResponse,
    NfcResultRequest,
    NfcResultResponse,
)
from app.services.feature_extractor import FeatureExtractor
from app.services.llm_service import LLMService
from app.services.risk_engine import RiskEngine
from app.services.website_analyzer import WebsiteAnalyzer


router = APIRouter(
    tags=["Risk Assessment"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Resource not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Server error"},
    },
)

_feature_extractor = FeatureExtractor()
_website_analyzer = WebsiteAnalyzer()
_risk_engine = RiskEngine()
_llm_service = LLMService()


@router.post(
    "/score/{session_id}",
    response_model=RiskResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute and persist a deterministic session risk assessment",
    responses={
        status.HTTP_200_OK: {"description": "Risk assessment computed successfully"},
        status.HTTP_404_NOT_FOUND: {"description": "No events found for session"},
    },
)
def get_risk_score(
    session_id: str,
    db: Session = Depends(get_db),
) -> RiskResponse:
    events = EventRepository(db).find_by_session(session_id)
    if not events:
        logger.warning("No events found for session_id={}", session_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No events found for this session",
        )

    # EventRepository returns chronological order, so the first match while
    # walking backward is the most recent analysis. Historical pages never
    # override the page currently being assessed.
    latest_page_event = next(
        (
            event
            for event in reversed(events)
            if str(event.event_type or "").upper() == "PAGE_ANALYSIS"
            and isinstance(event.payload, dict)
        ),
        None,
    )
    page_payload = latest_page_event.payload if latest_page_event is not None else None

    features = _feature_extractor.extract(page_payload, events)
    website_analysis = _website_analyzer.analyze(features)
    result = _risk_engine.calculate(features, website_analysis)
    explanation_result = _llm_service.explain_result(result)

    session_row = db.get(SessionModel, session_id)
    if session_row is None:
        session_row = SessionModel(id=session_id)
        db.add(session_row)
    session_row.current_risk_score = result["risk_score"]
    session_row.current_risk_level = result["risk_level"]
    db.commit()

    assessment = RiskAssessment(
        session_id=session_id,
        score=result["risk_score"],
        level=result["risk_level"],
        confidence=result["confidence"],
        triggered_rules=result["triggered_rules"],
        requires_physical_confirmation=result["requires_physical_confirmation"],
    )
    RiskRepository(db).save(assessment)

    selected_url = features["url_features"].get("url") or "n/a"
    logger.info(
        "Risk assessment session_id={} selected_url={} final_score={} confidence={} level={}",
        session_id,
        selected_url,
        result["risk_score"],
        result["confidence"],
        result["risk_level"],
    )
    if not explanation_result.get("available"):
        logger.warning(
            "LLM explanation fallback session_id={} reason={}",
            session_id,
            explanation_result.get("fallback_reason") or "unknown",
        )

    return RiskResponse(
        score=result["risk_score"],
        level=result["risk_level"],
        confidence=result["confidence"],
        triggered_rules=result["triggered_rules"],
        requires_physical_confirmation=result["requires_physical_confirmation"],
        explanation=explanation_result["explanation"],
    )


@router.get(
    "/risk/latest",
    response_model=LatestRiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch the most recent risk assessment across all sessions",
    responses={
        status.HTTP_200_OK: {"description": "Latest risk assessment returned"},
        status.HTTP_404_NOT_FOUND: {"description": "No risk assessments exist yet"},
    },
)
def get_latest_risk_assessment(
    db: Session = Depends(get_db),
) -> LatestRiskAssessmentResponse:
    """Used by the Arduino/GuardFlow hardware integration to poll for the
    newest verdict without needing to know a session_id in advance. The
    hardware side is responsible for deduplicating by `id`.
    """
    assessment = RiskRepository(db).get_latest()
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk assessments found",
        )

    return LatestRiskAssessmentResponse(
        id=assessment.id,
        session_id=assessment.session_id,
        score=int(assessment.score),
        level=assessment.level,
        confidence=int(assessment.confidence),
        requires_physical_confirmation=assessment.requires_physical_confirmation,
        physical_confirmation_result=assessment.physical_confirmation_result,
        created_at=assessment.created_at,
    )


@router.post(
    "/risk/{assessment_id}/nfc-result",
    response_model=NfcResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Report the outcome of a physical NFC confirmation",
    responses={
        status.HTTP_200_OK: {"description": "NFC result recorded"},
        status.HTTP_404_NOT_FOUND: {"description": "Assessment not found"},
    },
)
def report_nfc_result(
    assessment_id: str,
    body: NfcResultRequest,
    db: Session = Depends(get_db),
) -> NfcResultResponse:
    """Called by the Arduino/GuardFlow hardware side (via python/main.py)
    once a card has been tapped in the WAITING_FOR_NFC state and the
    sketch has resolved it to AUTHORIZED or DENIED.
    """
    repo = RiskRepository(db)
    assessment = repo.set_physical_confirmation_result(assessment_id, body.result)
    if assessment is None:
        logger.warning(
            "NFC result reported for unknown assessment_id={}", assessment_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk assessment not found",
        )

    logger.info(
        "NFC result recorded assessment_id={} session_id={} result={}",
        assessment.id,
        assessment.session_id,
        body.result,
    )

    return NfcResultResponse(
        id=assessment.id,
        session_id=assessment.session_id,
        physical_confirmation_result=assessment.physical_confirmation_result,
    )
