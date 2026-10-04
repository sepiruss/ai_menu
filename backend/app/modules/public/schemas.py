from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


class CustomerEventType(str, Enum):
    MENU_VIEW = "MENU_VIEW"
    CATEGORY_VIEW = "CATEGORY_VIEW"
    ITEM_VIEW = "ITEM_VIEW"
    ITEM_SEARCH = "ITEM_SEARCH"
    ADD_TO_CART = "ADD_TO_CART"
    REMOVE_FROM_CART = "REMOVE_FROM_CART"
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_CANCELLED = "ORDER_CANCELLED"


# QR Code schemas
class QRCodeBase(BaseModel):
    restaurant_id: int
    branch_id: int
    table_id: Optional[int] = None
    label: Optional[str] = None
    expires_at: Optional[datetime] = None


class QRCodeCreate(QRCodeBase):
    pass


class QRCodeUpdate(BaseModel):
    label: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class QRCodeResponse(QRCodeBase):
    id: int
    token: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Customer schemas
class CustomerBase(BaseModel):
    display_name: Optional[str] = None
    language: str = "fa"
    preferences: dict = Field(default_factory=dict)


class CustomerCreate(CustomerBase):
    external_id: Optional[str] = None


class CustomerUpdate(BaseModel):
    display_name: Optional[str] = None
    language: Optional[str] = None
    preferences: Optional[dict] = None
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    id: int
    restaurant_id: int
    external_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Customer Session schemas
class CustomerSessionBase(BaseModel):
    restaurant_id: int
    branch_id: int
    table_id: Optional[int] = None
    device_info: dict = Field(default_factory=dict)


class CustomerSessionCreate(CustomerSessionBase):
    customer_id: Optional[int] = None


class CustomerSessionResponse(CustomerSessionBase):
    id: int
    session_token: str
    customer_id: Optional[int] = None
    is_active: bool
    expires_at: datetime
    last_activity_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# Public QR Resolution schemas
class QRResolveRequest(BaseModel):
    session_token: Optional[str] = None
    device_info: dict = Field(default_factory=dict)


class QRContextResponse(BaseModel):
    restaurant_id: int
    restaurant_name: str
    restaurant_slug: str
    branch_id: int
    branch_name: str
    branch_code: str
    table_id: Optional[int] = None
    table_name: Optional[str] = None
    table_code: Optional[str] = None
    session_token: str
    language: str = "fa"


# Public Menu schemas
class PublicMenuItemOptionBase(BaseModel):
    name: str
    price_adjustment_toman: Decimal
    price_adjustment_rial: Decimal
    is_required: bool
    display_order: int
    options_config: dict


class PublicMenuItemOptionResponse(PublicMenuItemOptionBase):
    id: int
    menu_item_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PublicMenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price_toman: Decimal
    price_rial: Decimal
    is_available: bool
    is_popular: bool
    is_new: bool
    display_order: int
    image_url: Optional[str] = None
    item_metadata: dict
    allergens_tags: list[str]


class PublicMenuItemResponse(PublicMenuItemBase):
    id: int
    category_id: int
    created_at: datetime
    updated_at: datetime
    options: list[PublicMenuItemOptionResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class PublicMenuItemListResponse(BaseModel):
    items: list[PublicMenuItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PublicCategoryBase(BaseModel):
    name: str
    slug: str
    display_order: int
    is_visible: bool
    translation: dict


class PublicCategoryResponse(PublicCategoryBase):
    id: int
    menu_id: int
    parent_id: Optional[int] = None
    children: list["PublicCategoryResponse"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PublicMenuResponse(BaseModel):
    id: int
    branch_id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    branding: dict
    categories: list[PublicCategoryResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Search
class PublicSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    category_id: Optional[int] = None
    page: int = 1
    page_size: int = 20


# Event schemas
class CustomerEventCreate(BaseModel):
    event_type: CustomerEventType
    menu_item_id: Optional[int] = None
    category_id: Optional[int] = None
    metadata: dict = Field(default_factory=dict)


class CustomerEventResponse(BaseModel):
    id: int
    customer_id: Optional[int] = None
    session_id: Optional[int] = None
    restaurant_id: int
    branch_id: int
    table_id: Optional[int] = None
    event_type: CustomerEventType
    menu_item_id: Optional[int] = None
    category_id: Optional[int] = None
    metadata: dict
    created_at: datetime

    class Config:
        from_attributes = True


# Cart schemas
class CartItemOptionSnapshot(BaseModel):
    option_id: int
    name: str
    price_adjustment_toman: Decimal
    price_adjustment_rial: Decimal
    is_required: bool


class CartItemSnapshot(BaseModel):
    menu_item_id: int
    quantity: int
    unit_price_toman: Decimal
    unit_price_rial: Decimal
    selected_options: List[CartItemOptionSnapshot] = Field(default_factory=list)
    item_name_snapshot: str
    options_price_adjustment_toman: Decimal = Decimal("0")
    options_price_adjustment_rial: Decimal = Decimal("0")


class CartAddItemRequest(BaseModel):
    menu_item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    selected_options: List[CartItemOptionSnapshot] = Field(default_factory=list)


class CartUpdateItemRequest(BaseModel):
    quantity: Optional[int] = Field(None, gt=0)
    selected_options: Optional[List[CartItemOptionSnapshot]] = None


class CartItemResponse(BaseModel):
    id: int
    menu_item_id: int
    quantity: int
    unit_price_toman: Decimal
    unit_price_rial: Decimal
    selected_options: List[CartItemOptionSnapshot] = Field(default_factory=list)
    item_name_snapshot: str
    options_price_adjustment_toman: Decimal
    options_price_adjustment_rial: Decimal
    subtotal_toman: Decimal
    subtotal_rial: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    id: int
    customer_id: Optional[int] = None
    customer_session_id: int
    restaurant_id: int
    branch_id: int
    table_id: Optional[int] = None
    is_active: bool
    items: List[CartItemResponse] = Field(default_factory=list)
    subtotal_toman: Decimal
    subtotal_rial: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Order schemas
class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    SERVED = "SERVED"
    CANCELLED = "CANCELLED"


class OrderItemOptionSnapshot(BaseModel):
    option_id: int
    name: str
    price_adjustment_toman: Decimal
    price_adjustment_rial: Decimal
    is_required: bool


class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: Optional[int] = None
    item_name: str
    item_description: Optional[str] = None
    quantity: int
    unit_price_toman: Decimal
    unit_price_rial: Decimal
    selected_options: List[OrderItemOptionSnapshot] = Field(default_factory=list)
    options_price_adjustment_toman: Decimal
    options_price_adjustment_rial: Decimal
    subtotal_toman: Decimal
    subtotal_rial: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: Optional[int] = None
    customer_session_id: int
    restaurant_id: int
    branch_id: int
    table_id: Optional[int] = None
    status: OrderStatus
    subtotal_toman: Decimal
    subtotal_rial: Decimal
    discount_toman: Decimal
    discount_rial: Decimal
    total_toman: Decimal
    total_rial: Decimal
    currency: str
    customer_note: Optional[str] = None
    internal_note: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    preparing_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    served_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    items: List[OrderItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrderCreateRequest(BaseModel):
    idempotency_key: Optional[str] = None
    customer_note: Optional[str] = Field(None, max_length=1000)


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus
    internal_note: Optional[str] = Field(None, max_length=1000)


# Error responses
class PublicErrorResponse(BaseModel):
    error: str
    message: str
    details: dict = Field(default_factory=dict)
    request_id: str