from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BranchBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=50)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    settings: dict = Field(default_factory=dict)
    operating_hours: dict = Field(default_factory=dict)


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    address: Optional[str] = None
    phone: Optional[str] = Field(None, max_length=50)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    settings: Optional[dict] = None
    operating_hours: Optional[dict] = None
    is_active: Optional[bool] = None


class BranchResponse(BranchBase):
    id: int
    restaurant_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BranchListResponse(BaseModel):
    items: list[BranchResponse]
    total: int
    page: int
    page_size: int
    total_pages: int