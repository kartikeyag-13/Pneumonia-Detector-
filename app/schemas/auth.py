import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, value: str) -> str:
        # bcrypt silently truncates passwords longer than 72 bytes; reject
        # them up front so the truncation can never be exploited.
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 bytes")
        return value


class LoginRequest(BaseModel):
    """
    Login accepts either a username OR an email to identify the account.
    At least one of the two must be provided.
    """

    username: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("username must not be empty")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: EmailStr
    created_at: datetime
