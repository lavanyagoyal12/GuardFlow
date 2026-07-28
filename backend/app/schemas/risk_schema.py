from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

class RiskResponse(BaseModel):
    """Risk assessment response matching Android client expectations.
    
    Attributes:
        score: Numeric risk valuation (0-100)
        level: Categorical risk classification
        confidence: Assessment certainty percentage (0-100)
        triggered_rules: List of rule IDs that contributed to the score
        requires_physical_confirmation: Whether human approval needed
        explanation: Concise human-readable description for the mobile UI
    """

    score: int = Field(..., ge=0, le=100, examples=[95])
    level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., examples=["HIGH"])
    confidence: int = Field(..., gt=0, le=100, examples=[96])
    triggered_rules: List[str] = Field(default_factory=list)
    requires_physical_confirmation: bool = Field(default=False)
    # Optional/additive field already supported by the Android RiskResult.
    # The exact score and level above still come only from RiskEngine.
    explanation: Optional[str] = Field(default=None, max_length=600)

    @field_validator('triggered_rules')
    def validate_rule_ids(cls, value: List[str]) -> List[str]:
        """Ensure rule IDs are non-empty strings."""
        if any(not rule_id for rule_id in value):
            raise ValueError("rule IDs cannot be empty")
        return value

class LatestRiskAssessmentResponse(BaseModel):
    """Latest stored risk assessment, for the Arduino/GuardFlow hardware poller.

    Unlike RiskResponse (which is the direct output of POST /score/{session_id}
    for the Android client), this includes the assessment's own id and
    session_id so the hardware side can (a) deduplicate - only act on a
    given assessment id once - and (b) report an NFC result back against
    the correct row.
    """

    id: str = Field(..., examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    session_id: str
    score: int = Field(..., ge=0, le=100, examples=[95])
    level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(..., examples=["HIGH"])
    confidence: int = Field(..., gt=0, le=100, examples=[96])
    requires_physical_confirmation: bool = Field(default=False)
    physical_confirmation_result: Optional[Literal["AUTHORIZED", "DENIED"]] = None
    created_at: datetime


class NfcResultRequest(BaseModel):
    """Body for reporting a physical NFC confirmation outcome."""

    result: Literal["AUTHORIZED", "DENIED"]


class NfcResultResponse(BaseModel):
    """Response after recording an NFC confirmation outcome."""

    id: str
    session_id: str
    physical_confirmation_result: Optional[Literal["AUTHORIZED", "DENIED"]] = None
