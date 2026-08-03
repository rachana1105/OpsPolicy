"""OpsPolicy FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    analytics,
    approvals,
    audit,
    auth,
    exceptions,
    grants,
    health,
    notifications,
    org,
    policies,
    requests,
    resources,
)
from app.core.config import settings
from app.core.errors import OpsPolicyError, opspolicy_error_handler
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware

configure_logging()

app = FastAPI(
    title="OpsPolicy",
    version=settings.app_version,
    description="Enterprise Policy, Approval, Exception, and Compliance Management Platform",
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(OpsPolicyError, opspolicy_error_handler)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(org.router, prefix="/api/v1")
app.include_router(resources.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1")
app.include_router(requests.router, prefix="/api/v1")
app.include_router(approvals.router, prefix="/api/v1")
app.include_router(grants.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(exceptions.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"service": "OpsPolicy", "version": settings.app_version, "docs": "/docs"}
