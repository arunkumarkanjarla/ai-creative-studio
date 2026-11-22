
from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field
)


class UserCreate(BaseModel):

    name: str = Field(min_length=2, max_length=150)

    email: EmailStr

    mobile: str | None = Field(default=None, max_length=20)

    password: str = Field(min_length=12, max_length=128)

    role: Literal["user"] = "user"

    can_access_image: bool = False

    can_access_audio: bool = False

    can_access_video: bool = False


class UserUpdate(BaseModel):

    name: str | None = Field(default=None, min_length=2, max_length=150)

    mobile: str | None = Field(default=None, max_length=20)

    can_access_image: bool | None = None

    can_access_audio: bool | None = None

    can_access_video: bool | None = None

    is_active: bool | None = None


class UserResponse(BaseModel):

    id: int

    name: str

    email: EmailStr

    mobile: str | None

    role: str

    can_access_image: bool

    can_access_audio: bool

    can_access_video: bool

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"

    refresh_token: str | None = None

    expires_in: int | None = None


class RefreshRequest(BaseModel):

    refresh_token: str = Field(min_length=16)


class LogoutRequest(BaseModel):

    refresh_token: str | None = None

    all_devices: bool = False


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    mobile: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=12, max_length=128)
