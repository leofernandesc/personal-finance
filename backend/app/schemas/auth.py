from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import APIModel


class RegisterRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=120)
    timezone: str = Field(default="America/Manaus", max_length=64)


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(APIModel):
    id: UUID
    email: EmailStr
    full_name: str
    timezone: str


class AuthResponse(APIModel):
    user: UserResponse
