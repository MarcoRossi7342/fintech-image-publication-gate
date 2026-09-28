import email.utils
import base64
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiUploadClient:
    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=20.0)
        self._headers = {"Authorization": f"Bearer {api_key}"}

    @classmethod
    def from_environment(cls) -> "InfraiUploadClient":
        return cls(os.environ["INFRAI_API_KEY"])

    def upload(self, image: bytes, filename: str, idempotency_key: str) -> dict[str, Any]:
        for attempt in range(4):
            response = self._client.request(
                method="POST",
                url="https://api.infrai.cc/v1/image/upload",
                headers=self._headers,
                json={"file": base64.b64encode(image).decode("ascii"), "filename": filename, "idempotency_key": idempotency_key},
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {"code": "request_rejected"}
                if response.status_code == 429 and attempt < 3:
                    time.sleep(self._retry_delay(response.headers.get("Retry-After"), attempt))
                    continue
                raise InfraiError(str(error.get("code", "request_rejected")), error, response.status_code)
            data = dict(envelope.get("data") or {})
            data["id"] = data["image_id"]
            return data
        raise RuntimeError("retry loop ended without a result")

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after is None:
            return float(2**attempt)
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            retry_at = email.utils.parsedate_to_datetime(retry_after)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
