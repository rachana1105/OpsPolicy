from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    employee_type: str
    status: str
    organisation_id: str
    team_id: str | None = None
    manager_id: str | None = None

    class Config:
        from_attributes = True
