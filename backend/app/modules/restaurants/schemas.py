from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RestaurantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    timezone: str = Field(default="Asia/Tehran", max_length=100)
    settings: dict = Field(default_factory=dict)
    branding: dict = Field(default_factory=dict)


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    timezone: Optional[str] = Field(None, max_length=100)
    settings: Optional[dict] = None
    branding: Optional[dict] = None
    is_active: Optional[bool] = None


class RestaurantResponse(RestaurantBase):
    id: int
    is_active: bool
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RestaurantListResponse(BaseModel):
    items: list[RestaurantResponse]
    total: int
    page: int
    page_size: int
    total_pages: int