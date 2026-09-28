from fintech_moderation.moderation_policy import (
    ImageFindings,
    PaymentEvent,
    PublicationAction,
    decide_publication,
)


def payment(amount_minor: int) -> PaymentEvent:
    return PaymentEvent(
        event_id="pay_1042",
        account_id="acct_27",
        amount_minor=amount_minor,
        currency="USD",
    )


def test_high_value_payment_is_held_for_review() -> None:
    decision = decide_publication(
        payment(150_000),
        ImageFindings(adult_score=0.02, violence_score=0.01),
    )

    assert decision.action is PublicationAction.REVIEW
    assert decision.reason == "high_value_payment"


def test_explicit_content_is_rejected_before_publication() -> None:
    decision = decide_publication(
        payment(4_200),
        ImageFindings(adult_score=0.91, violence_score=0.01),
    )

    assert decision.action is PublicationAction.REJECT
    assert decision.reason == "adult_content"

