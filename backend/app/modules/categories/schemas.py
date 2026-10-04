from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[int] = None
    display_order: int = 0
    is_visible: bool = True
    translation: dict = Field(default_factory=dict)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    parent_id: Optional[int] = None
    display_order: Optional[int] = None
    is_visible: Optional[bool] = None
    translation: Optional[dict] = None


class CategoryResponse(CategoryBase):
    id: int
    menu_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CategoryTreeResponse(BaseModel):
    id: int
    menu_id: int
    name: str
    slug: str
    parent_id: Optional[int]
    display_order: int
    is_visible: bool
    translation: dict
    children: list["CategoryTreeResponse"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True