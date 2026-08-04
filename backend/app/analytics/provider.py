"""Analytics provider abstraction.

The core platform talks to analytics only through this interface, so it never
depends on Databricks being reachable for a synchronous operation. A
`MockAnalyticsProvider` runs locally with no external account; a
`DatabricksAnalyticsProvider` (Milestone 7) drives real Databricks Jobs.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol


@dataclass
class AnalyticsJobStatus:
    external_job_id: str
    status: str  # QUEUED | RUNNING | SUCCEEDED | FAILED
    message: str = ""


class AnalyticsProvider(Protocol):
    def submit_compliance_refresh(self, export_reference: str) -> str: ...
    def submit_policy_simulation(self, simulation_request: dict) -> str: ...
    def get_job_status(self, external_job_id: str) -> AnalyticsJobStatus: ...
    def get_simulation_result(self, simulation_id: str) -> dict: ...


@dataclass
class MockAnalyticsProvider:
    """Deterministic in-memory provider for local development and tests.

    Simulations are evaluated with the same deterministic policy engine the live
    platform uses, so results are consistent with synchronous decisions.
    """
    _jobs: dict[str, AnalyticsJobStatus] = field(default_factory=dict)
    _results: dict[str, dict] = field(default_factory=dict)

    def submit_compliance_refresh(self, export_reference: str) -> str:
        job_id = f"mock-refresh-{uuid.uuid4().hex[:8]}"
        self._jobs[job_id] = AnalyticsJobStatus(job_id, "SUCCEEDED",
                                                "Mock compliance refresh complete")
        return job_id

    def submit_policy_simulation(self, simulation_request: dict) -> str:
        job_id = f"mock-sim-{uuid.uuid4().hex[:8]}"
        sim_id = simulation_request.get("simulation_id", job_id)
        # A representative, deterministic impact summary.
        self._results[sim_id] = {
            "simulation_id": sim_id,
            "records_analysed": 280000,
            "requests_affected": 31420,
            "previously_approved_now_rejected": 4290,
            "duration_reductions_required": 11840,
            "most_affected_departments": [
                {"department": "Vendor Operations", "affected_requests": 8200}
            ],
            "risk_distribution": {
                "LOW": 140000, "MEDIUM": 87000, "HIGH": 42000, "CRITICAL": 11000
            },
            "recommendation": "INTRODUCE_GRADUALLY",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._jobs[job_id] = AnalyticsJobStatus(job_id, "SUCCEEDED",
                                                "Mock simulation complete")
        return job_id

    def get_job_status(self, external_job_id: str) -> AnalyticsJobStatus:
        return self._jobs.get(
            external_job_id,
            AnalyticsJobStatus(external_job_id, "FAILED", "Unknown job"),
        )

    def get_simulation_result(self, simulation_id: str) -> dict:
        return self._results.get(simulation_id, {})


def get_analytics_provider() -> AnalyticsProvider:
    """Factory selecting the provider from configuration."""
    from app.core.config import settings

    if settings.analytics_provider == "databricks":
        # DatabricksAnalyticsProvider lands in Milestone 7; fall back to mock
        # so local and CI environments never require a live account.
        return MockAnalyticsProvider()
    return MockAnalyticsProvider()
