from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.enums import Criticality, ResourceType, Sensitivity
from app.models.org import Resource, User

router = APIRouter(prefix="/resources", tags=["resources"])


class ResourceIn(BaseModel):
    name: str
    resource_type: ResourceType
    owner_user_id: str | None = None
    criticality: Criticality = Criticality.MEDIUM
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    region: str | None = None
    metadata: dict = {}


class ResourceOut(BaseModel):
    id: str
    name: str
    resource_type: str
    owner_user_id: str | None
    criticality: str
    sensitivity: str
    region: str | None
    is_active: bool

    class Config:
        from_attributes = True


def _out(r: Resource) -> ResourceOut:
    return ResourceOut(
        id=r.id, name=r.name, resource_type=r.resource_type.value,
        owner_user_id=r.owner_user_id, criticality=r.criticality.value,
        sensitivity=r.sensitivity.value, region=r.region, is_active=r.is_active,
    )


@router.get("", response_model=list[ResourceOut])
def list_resources(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Resource).where(Resource.organisation_id == user.organisation_id)
    return [_out(r) for r in db.execute(stmt).scalars().all()]


@router.get("/{resource_id}", response_model=ResourceOut)
def get_resource(resource_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.get(Resource, resource_id)
    if not r or r.organisation_id != user.organisation_id:
        raise NotFoundError("Resource not found.")
    return _out(r)


@router.post("", response_model=ResourceOut, status_code=201)
def create_resource(body: ResourceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = Resource(
        organisation_id=user.organisation_id,
        name=body.name, resource_type=body.resource_type,
        owner_user_id=body.owner_user_id, criticality=body.criticality,
        sensitivity=body.sensitivity, region=body.region, resource_metadata=body.metadata,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _out(r)


@router.put("/{resource_id}", response_model=ResourceOut)
def update_resource(resource_id: str, body: ResourceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.get(Resource, resource_id)
    if not r or r.organisation_id != user.organisation_id:
        raise NotFoundError("Resource not found.")
    r.name = body.name
    r.resource_type = body.resource_type
    r.owner_user_id = body.owner_user_id
    r.criticality = body.criticality
    r.sensitivity = body.sensitivity
    r.region = body.region
    r.resource_metadata = body.metadata
    db.commit()
    db.refresh(r)
    return _out(r)
