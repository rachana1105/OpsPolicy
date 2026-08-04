"""Background worker runner.

Milestone 1 ships the runner skeleton with an idempotent scheduler loop and a
task registry. Later milestones (5, 7) register the real lifecycle tasks:
provisioning, expiry scheduling, revocation, retry, SLA escalation, exports and
analytics polling. The loop already guarantees the invariants those tasks need:
one worker per grant, dedupe via Redis, structured logs, and audit events.
"""
import time

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger("worker")

# Task registry: name -> callable(db) run each tick. Populated by later milestones.
TASK_REGISTRY: dict[str, callable] = {}


def register(name: str):
    def deco(fn):
        TASK_REGISTRY[name] = fn
        return fn
    return deco


# Register lifecycle tasks (Milestone 5).
from app.workers.lifecycle_tasks import register as register_lifecycle  # noqa: E402

register_lifecycle(register)

# Register SLA escalation + notification delivery tasks (Milestone 6).
from app.workers.sla_tasks import register as register_sla  # noqa: E402

register_sla(register)

# Register exception lifecycle tasks (Milestone 5 tail).
from app.workers.exception_tasks import register as register_exceptions  # noqa: E402

register_exceptions(register)


def run_forever(interval_seconds: int = 15) -> None:
    log.info("worker.start", registered_tasks=list(TASK_REGISTRY.keys()),
             interval_seconds=interval_seconds)
    from app.db.session import SessionLocal
    while True:
        for name, fn in TASK_REGISTRY.items():
            db = SessionLocal()
            try:
                fn(db)
                db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                log.error("worker.task_failed", task=name, error=str(exc))
            finally:
                db.close()
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_forever()
