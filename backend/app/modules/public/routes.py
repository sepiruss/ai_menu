from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from decimal import Decimal
from app.core import get_db
from app.core.exceptions import NotFoundException, ValidationException
from app.core.models import QRCode, CustomerSession, Category, MenuItem, User
from app.modules.auth.dependencies import get_current_user
from app.modules.public.service import (
    QRCodeService, CustomerService, CustomerSessionService,
    PublicMenuService, CustomerEventService, CartService, OrderService
)
from app.modules.public.schemas import (
    QRCodeCreate, QRCodeUpdate, QRCodeResponse,
    QRResolveRequest, QRContextResponse,
    PublicMenuResponse, PublicCategoryResponse,
    PublicMenuItemResponse, PublicMenuItemListResponse,
    PublicMenuItemOptionResponse,
    PublicSearchRequest,
    CustomerEventCreate, CustomerEventResponse,
    CustomerEventType,
    CartAddItemRequest, CartUpdateItemRequest,
    CartItemResponse, CartResponse,
    OrderCreateRequest, OrderResponse, OrderListResponse,
    OrderStatus, OrderStatusUpdateRequest,
)

router = APIRouter(tags=["public"])


# Dependency injection
async def get_qr_service(db: AsyncSession = Depends(get_db)) -> QRCodeService:
    return QRCodeService(db)


async def get_customer_service(db: AsyncSession = Depends(get_db)) -> CustomerService:
    return CustomerService(db)


async def get_session_service(db: AsyncSession = Depends(get_db)) -> CustomerSessionService:
    return CustomerSessionService(db)


async def get_menu_service(db: AsyncSession = Depends(get_db)) -> PublicMenuService:
    return PublicMenuService(db)


async def get_event_service(db: AsyncSession = Depends(get_db)) -> CustomerEventService:
    return CustomerEventService(db)


async def get_cart_service(db: AsyncSession = Depends(get_db)) -> CartService:
    return CartService(db)


async def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db)


# QR Code resolution endpoint - main entry point for customers
@router.post("/qr/{token}", response_model=QRContextResponse, summary="Resolve QR code and create/get session")
async def resolve_qr(
    token: str,
    request: QRResolveRequest,
    qr_service: QRCodeService = Depends(get_qr_service),
    session_service: CustomerSessionService = Depends(get_session_service),
    event_service: CustomerEventService = Depends(get_event_service),
):
    """Resolve a QR code token and create/continue an anonymous customer session."""
    qr_code = await qr_service.get_by_token(token)
    
    if not qr_code.is_active:
        raise ValidationException("QR code is inactive")
    
    if qr_code.expires_at and qr_code.expires_at < datetime.now(timezone.utc):
        raise ValidationException("QR code has expired")
    
    # Create or get session
    session = await session_service.create_or_get(
        restaurant_id=qr_code.restaurant_id,
        branch_id=qr_code.branch_id,
        table_id=qr_code.table_id,
        session_token=request.session_token,
        device_info=request.device_info,
    )
    
    # Track MENU_VIEW event
    await event_service.track_event(
        CustomerEventCreate(event_type=CustomerEventType.MENU_VIEW),
        restaurant_id=qr_code.restaurant_id,
        branch_id=qr_code.branch_id,
        session_id=session.id,
        customer_id=session.customer_id,
        table_id=qr_code.table_id,
    )
    
    return QRContextResponse(
        restaurant_id=qr_code.restaurant_id,
        restaurant_name=qr_code.restaurant.name,
        restaurant_slug=qr_code.restaurant.slug,
        branch_id=qr_code.branch_id,
        branch_name=qr_code.branch.name,
        branch_code=qr_code.branch.code,
        table_id=qr_code.table_id,
        table_name=qr_code.table.name if qr_code.table else None,
        table_code=qr_code.table.code if qr_code.table else None,
        session_token=session.session_token,
        language=session.customer.language if session.customer else "fa",
    )


# Public Menu endpoints
@router.get("/menu/{branch_id}", response_model=PublicMenuResponse, summary="Get public menu for branch")
async def get_public_menu(
    branch_id: int,
    session_token: str = Header(..., alias="X-Session-Token"),
    menu_service: PublicMenuService = Depends(get_menu_service),
    session_service: CustomerSessionService = Depends(get_session_service),
    event_service: CustomerEventService = Depends(get_event_service),
):
    """Get the full public menu for a branch."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    if session.branch_id != branch_id:
        raise ValidationException("Session branch mismatch")
    
    menu = await menu_service.get_public_menu(branch_id, session.restaurant_id)
    if not menu:
        raise NotFoundException("Menu", branch_id)
    
    # Track MENU_VIEW event
    await event_service.track_event(
        CustomerEventCreate(event_type=CustomerEventType.MENU_VIEW),
        restaurant_id=session.restaurant_id,
        branch_id=branch_id,
        session_id=session.id,
        customer_id=session.customer_id,
        table_id=session.table_id,
    )
    
    # Build response with categories using service's tree builder
    category_responses = await _build_category_tree(menu.id, menu_service)
    
    return PublicMenuResponse(
        id=menu.id,
        branch_id=menu.branch_id,
        name=menu.name,
        description=menu.description,
        is_active=menu.is_active,
        branding=menu.branding,
        categories=category_responses,
        created_at=menu.created_at,
        updated_at=menu.updated_at,
    )


async def _build_category_tree(menu_id: int, menu_service: PublicMenuService) -> list[PublicCategoryResponse]:
    """Build category tree using service's category tree method."""
    root_categories = await menu_service.get_category_tree(menu_id)
    return [_category_to_response(cat) for cat in root_categories]


def _category_to_response(cat: Category) -> PublicCategoryResponse:
    """Convert Category model to PublicCategoryResponse without lazy loading."""
    # Use the attached _children_map if available, otherwise fall back to empty list
    children_map = getattr(cat, '_children_map', {})
    children = [_category_to_response(child) for child in children_map.get(cat.id, []) if child.is_visible]
    
    return PublicCategoryResponse(
        id=cat.id,
        menu_id=cat.menu_id,
        name=cat.name,
        slug=cat.slug,
        parent_id=cat.parent_id,
        display_order=cat.display_order,
        is_visible=cat.is_visible,
        translation=cat.translation,
        children=children,
        created_at=cat.created_at,
        updated_at=cat.updated_at,
    )


@router.get("/menu/{branch_id}/categories", response_model=list[PublicCategoryResponse], summary="Get public categories")
async def get_public_categories(
    branch_id: int,
    parent_id: Optional[int] = Query(None),
    session_token: str = Header(..., alias="X-Session-Token"),
    menu_service: PublicMenuService = Depends(get_menu_service),
    session_service: CustomerSessionService = Depends(get_session_service),
    event_service: CustomerEventService = Depends(get_event_service),
):
    """Get public categories for a branch."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    if session.branch_id != branch_id:
        raise ValidationException("Session branch mismatch")
    
    menu = await menu_service.get_public_menu(branch_id, session.restaurant_id)
    if not menu:
        raise NotFoundException("Menu", branch_id)
    
    if parent_id is not None:
        categories = await menu_service.get_categories(menu.id, parent_id)
        # Return flat list for parent_id filter
        return [
            PublicCategoryResponse(
                id=cat.id,
                menu_id=cat.menu_id,
                name=cat.name,
                slug=cat.slug,
                parent_id=cat.parent_id,
                display_order=cat.display_order,
                is_visible=cat.is_visible,
                translation=cat.translation,
                children=[],
                created_at=cat.created_at,
                updated_at=cat.updated_at,
            )
            for cat in categories if cat.is_visible
        ]
    else:
        # Get category tree with children
        root_categories = await menu_service.get_category_tree(menu.id)
        return [_category_to_response(cat) for cat in root_categories if cat.is_visible]


@router.get("/menu/{branch_id}/items", response_model=PublicMenuItemListResponse, summary="Get public menu items")
async def get_public_items(
    branch_id: int,
    category_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    is_popular: Optional[bool] = Query(None),
    is_new: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    session_token: str = Header(..., alias="X-Session-Token"),
    menu_service: PublicMenuService = Depends(get_menu_service),
    session_service: CustomerSessionService = Depends(get_session_service),
    event_service: CustomerEventService = Depends(get_event_service),
):
    """Get public menu items for a category."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    if session.branch_id != branch_id:
        raise ValidationException("Session branch mismatch")
    
    items, total = await menu_service.get_items(
        category_id=category_id,
        page=page,
        page_size=page_size,
        is_available=True,
        is_popular=is_popular,
        is_new=is_new,
        search=search,
    )
    
    # Track ITEM_SEARCH if search query provided, else just listing
    if search:
        await event_service.track_event(
            CustomerEventCreate(
                event_type=CustomerEventType.ITEM_SEARCH,
                metadata={"query": search, "category_id": category_id}
            ),
            restaurant_id=session.restaurant_id,
            branch_id=branch_id,
            session_id=session.id,
            customer_id=session.customer_id,
            table_id=session.table_id,
        )
    
    item_responses = []
    for item in items:
        option_responses = [
            PublicMenuItemOptionResponse(
                id=opt.id,
                menu_item_id=opt.menu_item_id,
                name=opt.name,
                price_adjustment_toman=opt.price_adjustment_toman,
                price_adjustment_rial=opt.price_adjustment_rial,
                is_required=opt.is_required,
                display_order=opt.display_order,
                options_config=opt.options_config,
                created_at=opt.created_at,
            )
            for opt in item.options
        ]
        item_responses.append(PublicMenuItemResponse(
            id=item.id,
            category_id=item.category_id,
            name=item.name,
            description=item.description,
            price_toman=item.price_toman,
            price_rial=item.price_rial,
            is_available=item.is_available,
            is_popular=item.is_popular,
            is_new=item.is_new,
            display_order=item.display_order,
            image_url=item.image_url,
            item_metadata=item.item_metadata,
            allergens_tags=item.allergens_tags,
            options=option_responses,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))
    
    return PublicMenuItemListResponse(
        items=item_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/menu/{branch_id}/items/{item_id}", response_model=PublicMenuItemResponse, summary="Get public menu item details")
async def get_public_item(
    branch_id: int,
    item_id: int,
    session_token: str = Header(..., alias="X-Session-Token"),
    menu_service: PublicMenuService = Depends(get_menu_service),
    session_service: CustomerSessionService = Depends(get_session_service),
    event_service: CustomerEventService = Depends(get_event_service),
):
    """Get public menu item details."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    if session.branch_id != branch_id:
        raise ValidationException("Session branch mismatch")
    
    item = await menu_service.get_item_by_id(item_id)
    if not item:
        raise NotFoundException("MenuItem", item_id)
    
    # Track ITEM_VIEW event
    await event_service.track_event(
        CustomerEventCreate(
            event_type=CustomerEventType.ITEM_VIEW,
            menu_item_id=item_id,
        ),
        restaurant_id=session.restaurant_id,
        branch_id=branch_id,
        session_id=session.id,
        customer_id=session.customer_id,
        table_id=session.table_id,
    )
    
    option_responses = [
        PublicMenuItemOptionResponse(
            id=opt.id,
            menu_item_id=opt.menu_item_id,
            name=opt.name,
            price_adjustment_toman=opt.price_adjustment_toman,
            price_adjustment_rial=opt.price_adjustment_rial,
            is_required=opt.is_required,
            display_order=opt.display_order,
            options_config=opt.options_config,
            created_at=opt.created_at,
        )
        for opt in item.options
    ]
    
    return PublicMenuItemResponse(
        id=item.id,
        category_id=item.category_id,
        name=item.name,
        description=item.description,
        price_toman=item.price_toman,
        price_rial=item.price_rial,
        is_available=item.is_available,
        is_popular=item.is_popular,
        is_new=item.is_new,
        display_order=item.display_order,
        image_url=item.image_url,
        item_metadata=item.item_metadata,
        allergens_tags=item.allergens_tags,
        options=option_responses,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/menu/{branch_id}/search", response_model=PublicMenuItemListResponse, summary="Search menu items")
async def search_items(
    branch_id: int,
    search_request: PublicSearchRequest,
    session_token: str = Header(..., alias="X-Session-Token"),
    menu_service: PublicMenuService = Depends(get_menu_service),
    session_service: CustomerSessionService = Depends(get_session_service),
    event_service: CustomerEventService = Depends(get_event_service),
):
    """Search public menu items."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    if session.branch_id != branch_id:
        raise ValidationException("Session branch mismatch")
    
    items, total = await menu_service.search_items(
        branch_id=branch_id,
        query=search_request.query,
        category_id=search_request.category_id,
        page=search_request.page,
        page_size=search_request.page_size,
    )
    
    # Track ITEM_SEARCH event
    await event_service.track_event(
        CustomerEventCreate(
            event_type=CustomerEventType.ITEM_SEARCH,
            metadata={"query": search_request.query, "category_id": search_request.category_id}
        ),
        restaurant_id=session.restaurant_id,
        branch_id=branch_id,
        session_id=session.id,
        customer_id=session.customer_id,
        table_id=session.table_id,
    )
    
    item_responses = []
    for item in items:
        option_responses = [
            PublicMenuItemOptionResponse(
                id=opt.id,
                menu_item_id=opt.menu_item_id,
                name=opt.name,
                price_adjustment_toman=opt.price_adjustment_toman,
                price_adjustment_rial=opt.price_adjustment_rial,
                is_required=opt.is_required,
                display_order=opt.display_order,
                options_config=opt.options_config,
                created_at=opt.created_at,
            )
            for opt in item.options
        ]
        item_responses.append(PublicMenuItemResponse(
            id=item.id,
            category_id=item.category_id,
            name=item.name,
            description=item.description,
            price_toman=item.price_toman,
            price_rial=item.price_rial,
            is_available=item.is_available,
            is_popular=item.is_popular,
            is_new=item.is_new,
            display_order=item.display_order,
            image_url=item.image_url,
            item_metadata=item.item_metadata,
            allergens_tags=item.allergens_tags,
            options=option_responses,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))
    
    return PublicMenuItemListResponse(
        items=item_responses,
        total=total,
        page=search_request.page,
        page_size=search_request.page_size,
        total_pages=(total + search_request.page_size - 1) // search_request.page_size,
    )


# Cart endpoints
@router.get("/cart", response_model=CartResponse, summary="Get current cart")
async def get_cart(
    session_token: str = Header(..., alias="X-Session-Token"),
    cart_service: CartService = Depends(get_cart_service),
    session_service: CustomerSessionService = Depends(get_session_service),
):
    """Get the current active cart for the session."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    cart = await cart_service.get_cart(session.id)
    if not cart:
        # Return empty cart response
        return CartResponse(
            id=0,
            customer_id=None,
            customer_session_id=session.id,
            restaurant_id=session.restaurant_id,
            branch_id=session.branch_id,
            table_id=session.table_id,
            is_active=False,
            items=[],
            subtotal_toman=Decimal("0"),
            subtotal_rial=Decimal("0"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    
    # Calculate subtotals
    subtotal_toman = Decimal("0")
    subtotal_rial = Decimal("0")
    item_responses = []
    
    for item in cart.items:
        item_subtotal_toman = item.unit_price_toman * item.quantity + item.options_price_adjustment_toman * item.quantity
        item_subtotal_rial = item.unit_price_rial * item.quantity + item.options_price_adjustment_rial * item.quantity
        subtotal_toman += item_subtotal_toman
        subtotal_rial += item_subtotal_rial
        
        option_responses = [
            CartItemOptionSnapshot(
                option_id=opt.get("option_id", 0),
                name=opt.get("name", ""),
                price_adjustment_toman=Decimal(str(opt.get("price_adjustment_toman", "0"))),
                price_adjustment_rial=Decimal(str(opt.get("price_adjustment_rial", "0"))),
                is_required=opt.get("is_required", False),
            )
            for opt in item.selected_options
        ]
        
        item_responses.append(CartItemResponse(
            id=item.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            unit_price_toman=item.unit_price_toman,
            unit_price_rial=item.unit_price_rial,
            selected_options=option_responses,
            item_name_snapshot=item.item_name_snapshot,
            options_price_adjustment_toman=item.options_price_adjustment_toman,
            options_price_adjustment_rial=item.options_price_adjustment_rial,
            subtotal_toman=item_subtotal_toman,
            subtotal_rial=item_subtotal_rial,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))
    
    return CartResponse(
        id=cart.id,
        customer_id=cart.customer_id,
        customer_session_id=cart.customer_session_id,
        restaurant_id=cart.restaurant_id,
        branch_id=cart.branch_id,
        table_id=cart.table_id,
        is_active=cart.is_active,
        items=item_responses,
        subtotal_toman=subtotal_toman,
        subtotal_rial=subtotal_rial,
        created_at=cart.created_at,
        updated_at=cart.updated_at,
    )


@router.post("/cart/items", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED, summary="Add item to cart")
async def add_cart_item(
    request: CartAddItemRequest,
    session_token: str = Header(..., alias="X-Session-Token"),
    cart_service: CartService = Depends(get_cart_service),
    session_service: CustomerSessionService = Depends(get_session_service),
    event_service: CustomerEventService = Depends(get_event_service),
):
    """Add an item to the cart."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    # Convert selected_options to list of dicts
    selected_options = [
        {
            "option_id": opt.option_id,
            "name": opt.name,
            "price_adjustment_toman": str(opt.price_adjustment_toman),
            "price_adjustment_rial": str(opt.price_adjustment_rial),
            "is_required": opt.is_required,
        }
        for opt in request.selected_options
    ]
    
    cart_item = await cart_service.add_item(
        session_id=session.id,
        menu_item_id=request.menu_item_id,
        quantity=request.quantity,
        selected_options=selected_options,
        restaurant_id=session.restaurant_id,
        branch_id=session.branch_id,
        table_id=session.table_id,
    )
    
    # Track ADD_TO_CART event
    await event_service.track_event(
        CustomerEventCreate(
            event_type=CustomerEventType.ADD_TO_CART,
            menu_item_id=request.menu_item_id,
            metadata={"quantity": request.quantity}
        ),
        restaurant_id=session.restaurant_id,
        branch_id=session.branch_id,
        session_id=session.id,
        customer_id=session.customer_id,
        table_id=session.table_id,
    )
    
    option_responses = [
        CartItemOptionSnapshot(
            option_id=opt.get("option_id", 0),
            name=opt.get("name", ""),
            price_adjustment_toman=Decimal(str(opt.get("price_adjustment_toman", "0"))),
            price_adjustment_rial=Decimal(str(opt.get("price_adjustment_rial", "0"))),
            is_required=opt.get("is_required", False),
        )
        for opt in cart_item.selected_options
    ]
    
    item_subtotal_toman = cart_item.unit_price_toman * cart_item.quantity + cart_item.options_price_adjustment_toman * cart_item.quantity
    item_subtotal_rial = cart_item.unit_price_rial * cart_item.quantity + cart_item.options_price_adjustment_rial * cart_item.quantity
    
    return CartItemResponse(
        id=cart_item.id,
        menu_item_id=cart_item.menu_item_id,
        quantity=cart_item.quantity,
        unit_price_toman=cart_item.unit_price_toman,
        unit_price_rial=cart_item.unit_price_rial,
        selected_options=option_responses,
        item_name_snapshot=cart_item.item_name_snapshot,
        options_price_adjustment_toman=cart_item.options_price_adjustment_toman,
        options_price_adjustment_rial=cart_item.options_price_adjustment_rial,
        subtotal_toman=item_subtotal_toman,
        subtotal_rial=item_subtotal_rial,
        created_at=cart_item.created_at,
        updated_at=cart_item.updated_at,
    )


@router.put("/cart/items/{item_id}", response_model=CartItemResponse, summary="Update cart item")
async def update_cart_item(
    item_id: int,
    request: CartUpdateItemRequest,
    session_token: str = Header(..., alias="X-Session-Token"),
    cart_service: CartService = Depends(get_cart_service),
    session_service: CustomerSessionService = Depends(get_session_service),
):
    """Update cart item quantity or selected options."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    # Convert selected_options to list of dicts if provided
    selected_options = None
    if request.selected_options is not None:
        selected_options = [
            {
                "option_id": opt.option_id,
                "name": opt.name,
                "price_adjustment_toman": str(opt.price_adjustment_toman),
                "price_adjustment_rial": str(opt.price_adjustment_rial),
                "is_required": opt.is_required,
            }
            for opt in request.selected_options
        ]
    
    cart_item = await cart_service.update_item(
        session_id=session.id,
        cart_item_id=item_id,
        quantity=request.quantity,
        selected_options=selected_options,
    )
    
    option_responses = [
        CartItemOptionSnapshot(
            option_id=opt.get("option_id", 0),
            name=opt.get("name", ""),
            price_adjustment_toman=Decimal(str(opt.get("price_adjustment_toman", "0"))),
            price_adjustment_rial=Decimal(str(opt.get("price_adjustment_rial", "0"))),
            is_required=opt.get("is_required", False),
        )
        for opt in cart_item.selected_options
    ]
    
    item_subtotal_toman = cart_item.unit_price_toman * cart_item.quantity + cart_item.options_price_adjustment_toman * cart_item.quantity
    item_subtotal_rial = cart_item.unit_price_rial * cart_item.quantity + cart_item.options_price_adjustment_rial * cart_item.quantity
    
    return CartItemResponse(
        id=cart_item.id,
        menu_item_id=cart_item.menu_item_id,
        quantity=cart_item.quantity,
        unit_price_toman=cart_item.unit_price_toman,
        unit_price_rial=cart_item.unit_price_rial,
        selected_options=option_responses,
        item_name_snapshot=cart_item.item_name_snapshot,
        options_price_adjustment_toman=cart_item.options_price_adjustment_toman,
        options_price_adjustment_rial=cart_item.options_price_adjustment_rial,
        subtotal_toman=item_subtotal_toman,
        subtotal_rial=item_subtotal_rial,
        created_at=cart_item.created_at,
        updated_at=cart_item.updated_at,
    )


@router.delete("/cart/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove item from cart")
async def remove_cart_item(
    item_id: int,
    session_token: str = Header(..., alias="X-Session-Token"),
    cart_service: CartService = Depends(get_cart_service),
    session_service: CustomerSessionService = Depends(get_session_service),
    event_service: CustomerEventService = Depends(get_event_service),
):
    """Remove an item from the cart."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    # Get cart item to track event before deletion
    cart = await cart_service.get_cart(session.id)
    if cart:
        for item in cart.items:
            if item.id == item_id:
                # Track REMOVE_FROM_CART event
                await event_service.track_event(
                    CustomerEventCreate(
                        event_type=CustomerEventType.REMOVE_FROM_CART,
                        menu_item_id=item.menu_item_id,
                        metadata={"quantity": item.quantity}
                    ),
                    restaurant_id=session.restaurant_id,
                    branch_id=session.branch_id,
                    session_id=session.id,
                    customer_id=session.customer_id,
                    table_id=session.table_id,
                )
                break
    
    await cart_service.remove_item(session_id=session.id, cart_item_id=item_id)


@router.delete("/cart", status_code=status.HTTP_204_NO_CONTENT, summary="Clear cart")
async def clear_cart(
    session_token: str = Header(..., alias="X-Session-Token"),
    cart_service: CartService = Depends(get_cart_service),
    session_service: CustomerSessionService = Depends(get_session_service),
):
    """Clear all items from the cart."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    await cart_service.clear_cart(session_id=session.id)


# Order endpoints
@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, summary="Create order from cart")
async def create_order(
    request: OrderCreateRequest,
    session_token: str = Header(..., alias="X-Session-Token"),
    order_service: OrderService = Depends(get_order_service),
    session_service: CustomerSessionService = Depends(get_session_service),
    event_service: CustomerEventService = Depends(get_event_service),
):
    """Create an order from the current cart."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    order = await order_service.create_order(
        session_id=session.id,
        idempotency_key=request.idempotency_key,
        customer_note=request.customer_note,
    )
    
    # Track ORDER_CREATED event
    await event_service.track_event(
        CustomerEventCreate(
            event_type=CustomerEventType.ORDER_CREATED,
            metadata={"order_id": order.id, "order_number": order.order_number}
        ),
        restaurant_id=session.restaurant_id,
        branch_id=session.branch_id,
        session_id=session.id,
        customer_id=session.customer_id,
        table_id=session.table_id,
    )
    
    # Build response with items
    item_responses = []
    for item in order.items:
        option_responses = [
            OrderItemOptionSnapshot(
                option_id=opt.get("option_id", 0),
                name=opt.get("name", ""),
                price_adjustment_toman=Decimal(str(opt.get("price_adjustment_toman", "0"))),
                price_adjustment_rial=Decimal(str(opt.get("price_adjustment_rial", "0"))),
                is_required=opt.get("is_required", False),
            )
            for opt in item.selected_options
        ]
        
        item_responses.append(OrderItemResponse(
            id=item.id,
            menu_item_id=item.menu_item_id,
            item_name=item.item_name,
            item_description=item.item_description,
            quantity=item.quantity,
            unit_price_toman=item.unit_price_toman,
            unit_price_rial=item.unit_price_rial,
            selected_options=option_responses,
            options_price_adjustment_toman=item.options_price_adjustment_toman,
            options_price_adjustment_rial=item.options_price_adjustment_rial,
            subtotal_toman=item.subtotal_toman,
            subtotal_rial=item.subtotal_rial,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))
    
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        customer_id=order.customer_id,
        customer_session_id=order.customer_session_id,
        restaurant_id=order.restaurant_id,
        branch_id=order.branch_id,
        table_id=order.table_id,
        status=order.status,
        subtotal_toman=order.subtotal_toman,
        subtotal_rial=order.subtotal_rial,
        discount_toman=order.discount_toman,
        discount_rial=order.discount_rial,
        total_toman=order.total_toman,
        total_rial=order.total_rial,
        currency=order.currency,
        customer_note=order.customer_note,
        internal_note=order.internal_note,
        confirmed_at=order.confirmed_at,
        preparing_at=order.preparing_at,
        ready_at=order.ready_at,
        served_at=order.served_at,
        cancelled_at=order.cancelled_at,
        cancellation_reason=order.cancellation_reason,
        items=item_responses,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.get("/orders", response_model=OrderListResponse, summary="Get orders for current session")
async def list_orders(
    session_token: str = Header(..., alias="X-Session-Token"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = Query(None),
    order_service: OrderService = Depends(get_order_service),
    session_service: CustomerSessionService = Depends(get_session_service),
):
    """Get orders for the current session."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    items, total = await order_service.list_orders(
        session_id=session.id,
        page=page,
        page_size=page_size,
        status=status,
    )
    
    item_responses = []
    for order in items:
        item_responses_inner = []
        for item in order.items:
            option_responses = [
                OrderItemOptionSnapshot(
                    option_id=opt.get("option_id", 0),
                    name=opt.get("name", ""),
                    price_adjustment_toman=Decimal(str(opt.get("price_adjustment_toman", "0"))),
                    price_adjustment_rial=Decimal(str(opt.get("price_adjustment_rial", "0"))),
                    is_required=opt.get("is_required", False),
                )
                for opt in item.selected_options
            ]
            
            item_responses_inner.append(OrderItemResponse(
                id=item.id,
                menu_item_id=item.menu_item_id,
                item_name=item.item_name,
                item_description=item.item_description,
                quantity=item.quantity,
                unit_price_toman=item.unit_price_toman,
                unit_price_rial=item.unit_price_rial,
                selected_options=option_responses,
                options_price_adjustment_toman=item.options_price_adjustment_toman,
                options_price_adjustment_rial=item.options_price_adjustment_rial,
                subtotal_toman=item.subtotal_toman,
                subtotal_rial=item.subtotal_rial,
                created_at=item.created_at,
                updated_at=item.updated_at,
            ))
        
        item_responses.append(OrderResponse(
            id=order.id,
            order_number=order.order_number,
            customer_id=order.customer_id,
            customer_session_id=order.customer_session_id,
            restaurant_id=order.restaurant_id,
            branch_id=order.branch_id,
            table_id=order.table_id,
            status=order.status,
            subtotal_toman=order.subtotal_toman,
            subtotal_rial=order.subtotal_rial,
            discount_toman=order.discount_toman,
            discount_rial=order.discount_rial,
            total_toman=order.total_toman,
            total_rial=order.total_rial,
            currency=order.currency,
            customer_note=order.customer_note,
            internal_note=order.internal_note,
            confirmed_at=order.confirmed_at,
            preparing_at=order.preparing_at,
            ready_at=order.ready_at,
            served_at=order.served_at,
            cancelled_at=order.cancelled_at,
            cancellation_reason=order.cancellation_reason,
            items=item_responses_inner,
            created_at=order.created_at,
            updated_at=order.updated_at,
        ))
    
    return OrderListResponse(
        items=item_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse, summary="Get order by ID")
async def get_order(
    order_id: int,
    session_token: str = Header(..., alias="X-Session-Token"),
    order_service: OrderService = Depends(get_order_service),
    session_service: CustomerSessionService = Depends(get_session_service),
):
    """Get a specific order by ID."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    order = await order_service.get_order(order_id, session.id)
    
    item_responses = []
    for item in order.items:
        option_responses = [
            OrderItemOptionSnapshot(
                option_id=opt.get("option_id", 0),
                name=opt.get("name", ""),
                price_adjustment_toman=Decimal(str(opt.get("price_adjustment_toman", "0"))),
                price_adjustment_rial=Decimal(str(opt.get("price_adjustment_rial", "0"))),
                is_required=opt.get("is_required", False),
            )
            for opt in item.selected_options
        ]
        
        item_responses.append(OrderItemResponse(
            id=item.id,
            menu_item_id=item.menu_item_id,
            item_name=item.item_name,
            item_description=item.item_description,
            quantity=item.quantity,
            unit_price_toman=item.unit_price_toman,
            unit_price_rial=item.unit_price_rial,
            selected_options=option_responses,
            options_price_adjustment_toman=item.options_price_adjustment_toman,
            options_price_adjustment_rial=item.options_price_adjustment_rial,
            subtotal_toman=item.subtotal_toman,
            subtotal_rial=item.subtotal_rial,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))
    
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        customer_id=order.customer_id,
        customer_session_id=order.customer_session_id,
        restaurant_id=order.restaurant_id,
        branch_id=order.branch_id,
        table_id=order.table_id,
        status=order.status,
        subtotal_toman=order.subtotal_toman,
        subtotal_rial=order.subtotal_rial,
        discount_toman=order.discount_toman,
        discount_rial=order.discount_rial,
        total_toman=order.total_toman,
        total_rial=order.total_rial,
        currency=order.currency,
        customer_note=order.customer_note,
        internal_note=order.internal_note,
        confirmed_at=order.confirmed_at,
        preparing_at=order.preparing_at,
        ready_at=order.ready_at,
        served_at=order.served_at,
        cancelled_at=order.cancelled_at,
        cancellation_reason=order.cancellation_reason,
        items=item_responses,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse, summary="Cancel order")
async def cancel_order(
    order_id: int,
    request: OrderStatusUpdateRequest,
    session_token: str = Header(..., alias="X-Session-Token"),
    order_service: OrderService = Depends(get_order_service),
    session_service: CustomerSessionService = Depends(get_session_service),
    event_service: CustomerEventService = Depends(get_event_service),
):
    """Cancel an order."""
    session = await session_service.get_by_token(session_token)
    if not session or not session.is_active:
        raise ValidationException("Invalid or expired session")
    
    order = await order_service.cancel_order(
        order_id=order_id,
        session_id=session.id,
        reason=request.internal_note,
    )
    
    # Track ORDER_CANCELLED event
    await event_service.track_event(
        CustomerEventCreate(
            event_type=CustomerEventType.ORDER_CANCELLED,
            metadata={"order_id": order.id, "order_number": order.order_number, "reason": request.internal_note}
        ),
        restaurant_id=session.restaurant_id,
        branch_id=session.branch_id,
        session_id=session.id,
        customer_id=session.customer_id,
        table_id=session.table_id,
    )
    
    # Build response
    item_responses = []
    for item in order.items:
        option_responses = [
            OrderItemOptionSnapshot(
                option_id=opt.get("option_id", 0),
                name=opt.get("name", ""),
                price_adjustment_toman=Decimal(str(opt.get("price_adjustment_toman", "0"))),
                price_adjustment_rial=Decimal(str(opt.get("price_adjustment_rial", "0"))),
                is_required=opt.get("is_required", False),
            )
            for opt in item.selected_options
        ]
        
        item_responses.append(OrderItemResponse(
            id=item.id,
            menu_item_id=item.menu_item_id,
            item_name=item.item_name,
            item_description=item.item_description,
            quantity=item.quantity,
            unit_price_toman=item.unit_price_toman,
            unit_price_rial=item.unit_price_rial,
            selected_options=option_responses,
            options_price_adjustment_toman=item.options_price_adjustment_toman,
            options_price_adjustment_rial=item.options_price_adjustment_rial,
            subtotal_toman=item.subtotal_toman,
            subtotal_rial=item.subtotal_rial,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))
    
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        customer_id=order.customer_id,
        customer_session_id=order.customer_session_id,
        restaurant_id=order.restaurant_id,
        branch_id=order.branch_id,
        table_id=order.table_id,
        status=order.status,
        subtotal_toman=order.subtotal_toman,
        subtotal_rial=order.subtotal_rial,
        discount_toman=order.discount_toman,
        discount_rial=order.discount_rial,
        total_toman=order.total_toman,
        total_rial=order.total_rial,
        currency=order.currency,
        customer_note=order.customer_note,
        internal_note=order.internal_note,
        confirmed_at=order.confirmed_at,
        preparing_at=order.preparing_at,
        ready_at=order.ready_at,
        served_at=order.served_at,
        cancelled_at=order.cancelled_at,
        cancellation_reason=order.cancellation_reason,
        items=item_responses,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


# Admin QR Code management endpoints
@router.post("/admin/qr-codes", response_model=QRCodeResponse, status_code=status.HTTP_201_CREATED, summary="Create QR code")
async def create_qr_code(
    data: QRCodeCreate,
    current_user: "User" = Depends(get_current_user),  # Will need to import
    service: QRCodeService = Depends(get_qr_service),
):
    return await service.create(data)


@router.get("/admin/qr-codes", response_model=list[QRCodeResponse], summary="List QR codes")
async def list_qr_codes(
    restaurant_id: int = Query(...),
    branch_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    current_user: "User" = Depends(get_current_user),
    service: QRCodeService = Depends(get_qr_service),
):
    items, total = await service.list(restaurant_id, branch_id, page, page_size, is_active)
    return items


@router.get("/admin/qr-codes/{qr_id}", response_model=QRCodeResponse, summary="Get QR code")
async def get_qr_code(
    qr_id: int,
    restaurant_id: int = Query(...),
    current_user: "User" = Depends(get_current_user),
    service: QRCodeService = Depends(get_qr_service),
):
    return await service.get_by_id(qr_id, restaurant_id)


@router.put("/admin/qr-codes/{qr_id}", response_model=QRCodeResponse, summary="Update QR code")
async def update_qr_code(
    qr_id: int,
    data: QRCodeUpdate,
    restaurant_id: int = Query(...),
    current_user: "User" = Depends(get_current_user),
    service: QRCodeService = Depends(get_qr_service),
):
    return await service.update(qr_id, data, restaurant_id)


@router.delete("/admin/qr-codes/{qr_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete QR code")
async def delete_qr_code(
    qr_id: int,
    restaurant_id: int = Query(...),
    current_user: "User" = Depends(get_current_user),
    service: QRCodeService = Depends(get_qr_service),
):
    await service.delete(qr_id, restaurant_id)