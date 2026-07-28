from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.risk_assessment import RiskAssessment


class RiskRepository:
    """Database operations for RiskAssessment model using Repository pattern.

    Mirrors EventRepository's shape for consistency with the rest of the codebase.
    """

    def __init__(self, db: Session):
        self.db = db

    def save(self, assessment: RiskAssessment) -> RiskAssessment:
        """Persist a risk assessment to the database.

        Args:
            assessment: RiskAssessment model instance to save

        Returns:
            The persisted RiskAssessment with any database-generated values
        """
        self.db.add(assessment)
        self.db.commit()
        self.db.refresh(assessment)
        return assessment

    def get_latest_by_session(self, session_id: str) -> Optional[RiskAssessment]:
        """Retrieve the most recent risk assessment for a session.

        Args:
            session_id: Session identifier to filter by

        Returns:
            The latest RiskAssessment for the session, or None if none exist
        """
        stmt = (
            select(RiskAssessment)
            .where(RiskAssessment.session_id == session_id)
            .order_by(RiskAssessment.created_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest(self) -> Optional[RiskAssessment]:
        """Retrieve the most recent risk assessment across all sessions.

        Used by the Arduino/GuardFlow hardware integration, which has no
        session_id of its own and just wants "whatever the newest verdict
        is right now".

        Returns:
            The single newest RiskAssessment row, or None if the table is empty
        """
        stmt = select(RiskAssessment).order_by(RiskAssessment.created_at.desc()).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, assessment_id: str) -> Optional[RiskAssessment]:
        """Retrieve a single risk assessment by its primary key."""
        return self.db.get(RiskAssessment, assessment_id)

    def set_physical_confirmation_result(
        self, assessment_id: str, result: str
    ) -> Optional[RiskAssessment]:
        """Record the outcome of a physical NFC confirmation for an assessment.

        Args:
            assessment_id: Primary key of the RiskAssessment to update
            result: "AUTHORIZED" or "DENIED"

        Returns:
            The updated RiskAssessment, or None if no row with that id exists
        """
        assessment = self.get_by_id(assessment_id)
        if assessment is None:
            return None
        assessment.physical_confirmation_result = result
        self.db.commit()
        self.db.refresh(assessment)
        return assessment
