from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.org import User
from app.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: str
    notification_type: str
    subject: str
    body: str | None
    status: str
    attempts: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[NotificationOut])
def my_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notes = NotificationService(db).list_for_user(user.id)
    return [NotificationOut.model_validate(n) for n in notes]
