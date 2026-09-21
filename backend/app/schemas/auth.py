from uuid import UUID

from pydantic import EmailStr, Field, field_validator, model_validator

from app.schemas.common import APIModel


class RegisterRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=120)
    timezone: str = Field(default="America/Manaus", max_length=64)


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(APIModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        normalized = value.strip() if value is not None else None
        if normalized == "":
            raise ValueError("O nome não pode ficar vazio")
        return normalized

    @model_validator(mode="after")
    def require_update(self) -> "ProfileUpdateRequest":
        if self.full_name is None and self.timezone is None:
            raise ValueError("Informe ao menos um dado para atualizar")
        return self


class UserResponse(APIModel):
    id: UUID
    email: EmailStr
    full_name: str
    timezone: str


class AuthResponse(APIModel):
    user: UserResponse
