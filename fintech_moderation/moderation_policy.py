from enum import Enum

from pydantic import BaseModel, Field


class PublicationAction(str, Enum):
    PUBLISH = "publish"
    REVIEW = "review"
    REJECT = "reject"


class PaymentEvent(BaseModel):
    event_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    amount_minor: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class ImageFindings(BaseModel):
    adult_score: float = Field(ge=0.0, le=1.0)
    violence_score: float = Field(ge=0.0, le=1.0)


class ModerationDecision(BaseModel):
    action: PublicationAction
    reason: str


def decide_publication(event: PaymentEvent, findings: ImageFindings) -> ModerationDecision:
    if findings.adult_score >= 0.85:
        return ModerationDecision(action=PublicationAction.REJECT, reason="adult_content")
    if max(findings.adult_score, findings.violence_score) >= 0.65:
        return ModerationDecision(action=PublicationAction.REVIEW, reason="elevated_image_risk")
    if event.amount_minor >= 100_000:
        return ModerationDecision(action=PublicationAction.REVIEW, reason="high_value_payment")
    return ModerationDecision(action=PublicationAction.PUBLISH, reason="policy_passed")

