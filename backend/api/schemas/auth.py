"""Authentication schemas"""
from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: str | None = None
    user_id: int | None = None
    plan: str = "free"  # free, pro, team


class UserResponse(BaseModel):
    id: int
    email: str
    is_verified: bool
    created_at: str

    class Config:
        from_attributes = True
