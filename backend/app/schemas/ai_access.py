from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class StudioAccessUpdate(BaseModel):
    guest_access_enabled: bool | None = None
    guest_generation_limit: int | None = Field(default=None, ge=0, le=10000)
    guest_limit_period: Literal["day", "week", "month", "lifetime"] | None = None

    authenticated_limit_enabled: bool | None = None
    authenticated_generation_limit: int | None = Field(
        default=None, ge=0, le=100000
    )


class StudioAccessResponse(BaseModel):
    id: int
    studio: str
    guest_access_enabled: bool
    guest_generation_limit: int
    guest_limit_period: str
    authenticated_limit_enabled: bool
    authenticated_generation_limit: int | None

    model_config = ConfigDict(from_attributes=True)