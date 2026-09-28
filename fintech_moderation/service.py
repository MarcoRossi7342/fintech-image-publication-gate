import base64
import binascii
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_upload import InfraiError, InfraiUploadClient
from .moderation_policy import ImageFindings, PaymentEvent, PublicationAction, decide_publication


class ModerationRequest(BaseModel):
    event: PaymentEvent
    filename: str = Field(min_length=1)
    content_base64: str = Field(min_length=1)
    findings: ImageFindings


class AuditRecord(BaseModel):
    event_id: str
    action: PublicationAction
    reason: str


class RiskNotification(BaseModel):
    account_id: str
    event_id: str
    severity: str
    message: str


class ModerationResponse(BaseModel):
    action: PublicationAction
    state: str
    image_id: str | None
    audit: AuditRecord
    notification: RiskNotification


app = FastAPI(title="Payment image publication gate")


def _result(request: ModerationRequest, action: PublicationAction, reason: str, image_id: str | None) -> ModerationResponse:
    state = {PublicationAction.PUBLISH: "live", PublicationAction.REVIEW: "held", PublicationAction.REJECT: "rejected"}[action]
    severity = {PublicationAction.PUBLISH: "info", PublicationAction.REVIEW: "warning", PublicationAction.REJECT: "critical"}[action]
    return ModerationResponse(
        action=action,
        state=state,
        image_id=image_id,
        audit=AuditRecord(event_id=request.event.event_id, action=action, reason=reason),
        notification=RiskNotification(
            account_id=request.event.account_id,
            event_id=request.event.event_id,
            severity=severity,
            message=f"Payment image decision: {action.value}",
        ),
    )


@app.post("/payment-images/decide", response_model=ModerationResponse)
def moderate_payment_image(request: ModerationRequest) -> ModerationResponse:
    decision = decide_publication(request.event, request.findings)
    if decision.action is not PublicationAction.PUBLISH:
        return _result(request, decision.action, decision.reason, None)
    try:
        image = base64.b64decode(request.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="content_base64 must contain valid base64") from exc

    try:
        data: dict[str, Any] = InfraiUploadClient.from_environment().upload(
            image=image,
            filename=request.filename,
            idempotency_key=request.event.event_id,
        )
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail={"code": exc.code, "error": exc.detail}) from exc

    image_id = str(data["id"])
    return _result(request, decision.action, decision.reason, image_id)

