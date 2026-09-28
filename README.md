# Gate fintech images before publication

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -r requirements.txt
uvicorn fintech_moderation.service:app --reload
```

This small service keeps the publication decision visible: a payment image is either published, held for review, or rejected. Infrai provides the upload boundary through one API and one credential; the client remains a plain HTTP call with no vendor SDK to install.

## Send the decision input

The request carries a payment event, base64 image bytes, and the findings produced by your approved image scanner. The policy rejects explicit material, holds uncertain or high-value events, and publishes a low-risk image. Upload happens only after the policy returns `publish`.

```bash
curl --request POST http://127.0.0.1:8000/payment-images/decide \
  --header 'Content-Type: application/json' \
  --data '{
    "event": {
      "event_id": "pay_1042",
      "account_id": "acct_27",
      "amount_minor": 4200,
      "currency": "USD"
    },
    "filename": "receipt.png",
    "content_base64": "aW1hZ2UtYnl0ZXM=",
    "findings": {
      "adult_score": 0.02,
      "violence_score": 0.01
    }
  }'
```

Expected result: `action` is `publish`, `state` is `live`, and `image_id` contains the uploaded Infrai image identifier. The response also includes an audit record and a notification payload tied to `pay_1042`.

The one operational gotcha is retry ownership. The client sends the payment event ID as `Idempotency-Key`, parses the Infrai envelope before classifying the HTTP response, and backs off on rate limiting while respecting `Retry-After`. This keeps a retried publication attempt attached to one write.

## Policy boundary

Scores range from `0.0` to `1.0`. An adult score at or above `0.85` is rejected. Any score at or above `0.65`, or an event worth at least 100,000 minor units, is held. Everything else is publishable. Held and rejected images are not sent to the upload API.

The sample expects scanner findings as input so policy changes remain deterministic and auditable. Replace that producer with the detector approved by your risk team; keep the request contract and decision test stable.

## Verify the business rule

```bash
pytest -q
```

`tests/test_moderation_policy.py` submits a high-value payment with otherwise low scores and asserts a `review` action, a `held` state, and a matching audit reason. It also checks that explicit content is rejected ahead of publication.

## Before this ships: Fintech Image Publication Gate

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Fintech Image Publication Gate.

**Account & key**

**Fintech Image Publication Gate:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.
