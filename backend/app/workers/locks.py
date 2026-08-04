"""Distributed per-entity locks so only one worker processes a grant at a time.

Uses Redis SET NX with a short TTL. If Redis is unavailable, the lock is treated
as acquired (a no-op) — correctness still holds because the lifecycle service's
DB-level guards (terminal revocation status, unique grant key, optimistic
locking) prevent duplicate side effects; the lock is a performance/coordination
optimisation, not the sole safety mechanism.
"""
from __future__ import annotations

from contextlib import contextmanager

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("worker.lock")

_LOCK_TTL_SECONDS = 30


@contextmanager
def grant_lock(key: str):
    client = None
    token = None
    try:
        import redis  # local import so tests without redis still run

        client = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        token = "1"
        acquired = client.set(f"opspolicy:lock:{key}", token, nx=True, ex=_LOCK_TTL_SECONDS)
        if not acquired:
            yield False
            return
        yield True
    except Exception as exc:  # noqa: BLE001 — Redis down or absent
        log.info("lock_fallback", key=key, reason=str(exc)[:80])
        yield True  # proceed; DB guards protect correctness
    finally:
        if client is not None:
            try:
                client.delete(f"opspolicy:lock:{key}")
            except Exception:  # noqa: BLE001
                pass
