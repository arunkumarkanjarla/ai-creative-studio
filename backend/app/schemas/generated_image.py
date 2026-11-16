from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=2000)
    prompt_id: str | None = Field(default=None, max_length=120)
    negative_prompt: str | None = Field(default=None, max_length=2000)


class ImageGenerateResponse(BaseModel):
    id: int
    prompt: str
    negative_prompt: str | None = None
    status: str
    image_url: str | None = None
    model_name: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    generation_time_seconds: Decimal | None = None
    error_message: str | None = None
    prompt_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptPackItem(BaseModel):
    prompt_id: str
    title: str
    description: str = ""
    base_prompt: str
    negative_prompt: str
    created_by: str = "user"
    created_at: str | None = None
    has_reference: bool = False
    reference_url: str | None = None


class ImageHistoryItem(BaseModel):
    id: int
    user_id: int | None = None
    visitor_id: str | None = None
    user_name: str | None = None
    user_email: str | None = None

    prompt: str
    negative_prompt: str | None = None

    model_name: str | None = None
    image_url: str | None = None
    image_path: str | None = None
    thumbnail_path: str | None = None

    image_width: int | None = None
    image_height: int | None = None
    image_format: str | None = None

    status: str
    error_message: str | None = None

    generation_time_seconds: Decimal | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImageHistoryResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[ImageHistoryItem]
