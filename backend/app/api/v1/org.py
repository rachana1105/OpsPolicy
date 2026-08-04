from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.org import Department, Organisation, Team, User
from app.schemas.auth import UserOut

router = APIRouter(tags=["organisation"])


@router.get("/organisation")
def get_organisation(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org = db.get(Organisation, user.organisation_id)
    if not org:
        raise NotFoundError("Organisation not found.")
    return {"id": org.id, "name": org.name}


@router.get("/users", response_model=list[UserOut])
def list_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(User).where(User.organisation_id == user.organisation_id)
    return [UserOut.model_validate(u) for u in db.execute(stmt).scalars().all()]


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target or target.organisation_id != user.organisation_id:
        raise NotFoundError("User not found.")
    return UserOut.model_validate(target)


@router.get("/teams")
def list_teams(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    teams = db.execute(select(Team)).scalars().all()
    return [{"id": t.id, "name": t.name, "department_id": t.department_id} for t in teams]


@router.get("/departments")
def list_departments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deps = db.execute(select(Department)).scalars().all()
    return [{"id": d.id, "name": d.name, "business_unit_id": d.business_unit_id} for d in deps]
