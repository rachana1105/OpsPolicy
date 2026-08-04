import redis
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["health"])


def _check_db() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        client = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


@router.get("/health")
def health():
    return {"status": "healthy", "version": settings.app_version}


@router.get("/health/ready")
def ready():
    db_ok = _check_db()
    redis_ok = _check_redis()
    # Analytics provider failure must NOT make the core service unhealthy.
    analytics = "available" if settings.analytics_provider == "mock" else "configured"
    status = "healthy" if db_ok and redis_ok else "degraded"
    return {
        "status": status,
        "database": "connected" if db_ok else "unavailable",
        "redis": "connected" if redis_ok else "unavailable",
        "analytics_provider": analytics,
        "version": settings.app_version,
    }
