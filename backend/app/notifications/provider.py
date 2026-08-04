"""Mock notification provider.

No real email or Slack account. Delivery outcomes are deterministic from the
notification id so demos are reproducible: the vast majority succeed, a small
share fail transiently to exercise the retry path.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass
class DeliveryResult:
    delivered: bool
    detail: str = ""


class MockNotificationProvider:
    def send(self, *, notification_id: str, user_id: str, subject: str,
             body: str | None, force: str | None = None) -> DeliveryResult:
        if force == "fail":
            return DeliveryResult(False, "Forced failure")
        if force == "ok":
            return DeliveryResult(True, "Forced success")
        bucket = int(hashlib.sha256(notification_id.encode()).hexdigest()[:8], 16) % 100
        if bucket < 90:
            return DeliveryResult(True, "delivered")
        return DeliveryResult(False, "transient provider error")
