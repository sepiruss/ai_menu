from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MenuBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: bool = True
    is_default: bool = False
    branding: dict = Field(default_factory=dict)


class MenuCreate(MenuBase):
    pass


class MenuUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    branding: Optional[dict] = None


class MenuResponse(MenuBase):
    id: int
    branch_id: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MenuListResponse(BaseModel):
    items: list[MenuResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MenuWithCategoriesResponse(MenuResponse):
    categories: list = Field(default_factory=list)