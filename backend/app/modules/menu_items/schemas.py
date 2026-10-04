from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class MenuItemOptionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    price_adjustment_toman: Decimal = Field(default=Decimal("0"), ge=0)
    price_adjustment_rial: Decimal = Field(default=Decimal("0"), ge=0)
    is_required: bool = False
    display_order: int = 0
    options_config: dict = Field(default_factory=dict)


class MenuItemOptionCreate(MenuItemOptionBase):
    pass


class MenuItemOptionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price_adjustment_toman: Optional[Decimal] = Field(None, ge=0)
    price_adjustment_rial: Optional[Decimal] = Field(None, ge=0)
    is_required: Optional[bool] = None
    display_order: Optional[int] = None
    options_config: Optional[dict] = None


class MenuItemOptionResponse(MenuItemOptionBase):
    id: int
    menu_item_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MenuItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price_toman: Decimal = Field(..., ge=0)
    price_rial: Decimal = Field(..., ge=0)
    is_available: bool = True
    is_popular: bool = False
    is_new: bool = False
    display_order: int = 0
    image_url: Optional[str] = Field(None, max_length=500)
    item_metadata: dict = Field(default_factory=dict)
    allergens_tags: list[str] = Field(default_factory=list)


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price_toman: Optional[Decimal] = Field(None, ge=0)
    price_rial: Optional[Decimal] = Field(None, ge=0)
    is_available: Optional[bool] = None
    is_popular: Optional[bool] = None
    is_new: Optional[bool] = None
    display_order: Optional[int] = None
    image_url: Optional[str] = Field(None, max_length=500)
    item_metadata: Optional[dict] = None
    allergens_tags: Optional[list[str]] = None


class MenuItemResponse(BaseModel):
    id: int
    category_id: int
    name: str
    description: Optional[str] = None
    price_toman: Decimal
    price_rial: Decimal
    is_available: bool
    is_popular: bool
    is_new: bool
    display_order: int
    image_url: Optional[str] = None
    item_metadata: dict = Field(default_factory=dict)
    allergens_tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class MenuItemDetailResponse(MenuItemResponse):
    options: list[MenuItemOptionResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
        populate_by_name = True


class MenuItemListResponse(BaseModel):
    items: list[MenuItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int