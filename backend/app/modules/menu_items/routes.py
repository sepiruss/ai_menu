from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import get_db
from app.core.models import User
from app.modules.auth.dependencies import get_current_user, require_owner_or_admin
from app.modules.restaurants.service import RestaurantService
from app.modules.branches.service import BranchService
from app.modules.menus.service import MenuService
from app.modules.categories.service import CategoryService
from app.modules.menu_items.schemas import (
    MenuItemCreate, MenuItemUpdate, MenuItemResponse, MenuItemListResponse,
    MenuItemDetailResponse, MenuItemOptionCreate, MenuItemOptionUpdate, MenuItemOptionResponse
)
from app.modules.menu_items.service import MenuItemService


router = APIRouter()


async def get_menu_item_service(db: AsyncSession = Depends(get_db)) -> MenuItemService:
    return MenuItemService(db)


async def get_restaurant_service(db: AsyncSession = Depends(get_db)) -> RestaurantService:
    return RestaurantService(db)


async def get_branch_service(db: AsyncSession = Depends(get_db)) -> BranchService:
    return BranchService(db)


async def get_menu_service(db: AsyncSession = Depends(get_db)) -> MenuService:
    return MenuService(db)


async def get_category_service(db: AsyncSession = Depends(get_db)) -> CategoryService:
    return CategoryService(db)


async def verify_category_access(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    current_user: User = Depends(get_current_user),
    restaurant_service: RestaurantService = Depends(get_restaurant_service),
    branch_service: BranchService = Depends(get_branch_service),
    menu_service: MenuService = Depends(get_menu_service),
    category_service: CategoryService = Depends(get_category_service),
) -> int:
    """Verify user has access to restaurant, branch, menu, and category"""
    if current_user.is_superuser:
        return category_id
    
    has_access = await restaurant_service.check_ownership(restaurant_id, current_user.id)
    if not has_access:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Access denied to this restaurant")
    
    branch = await branch_service.get_by_id(branch_id, restaurant_id)
    menu = await menu_service.get_by_id(menu_id, branch_id)
    category = await category_service.get_by_id(category_id, menu_id)
    return category.id


# Menu Item routes
@router.post(
    "/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}/items",
    response_model=MenuItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create menu item"
)
async def create_menu_item(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    data: MenuItemCreate,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
    _: int = Depends(verify_category_access),
):
    return await service.create(category_id, data)


@router.get(
    "/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}/items",
    response_model=MenuItemListResponse,
    summary="List menu items"
)
async def list_menu_items(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_available: bool | None = Query(None),
    is_popular: bool | None = Query(None),
    is_new: bool | None = Query(None),
    search: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
    _: int = Depends(verify_category_access),
):
    items, total = await service.get_list(
        category_id, page, page_size, is_available, is_popular, is_new, search
    )
    return MenuItemListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}/items/{item_id}",
    response_model=MenuItemDetailResponse,
    summary="Get menu item"
)
async def get_menu_item(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
    _: int = Depends(verify_category_access),
):
    return await service.get_by_id(item_id, category_id)


@router.put(
    "/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}/items/{item_id}",
    response_model=MenuItemResponse,
    summary="Update menu item"
)
async def update_menu_item(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    item_id: int,
    data: MenuItemUpdate,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
    _: int = Depends(verify_category_access),
):
    return await service.update(item_id, data, category_id)


@router.delete(
    "/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete menu item (soft)"
)
async def delete_menu_item(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
    _: int = Depends(verify_category_access),
):
    await service.delete(item_id, category_id)


# Menu Item Options routes
@router.post(
    "/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}/items/{item_id}/options",
    response_model=MenuItemOptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create menu item option"
)
async def create_menu_item_option(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    item_id: int,
    data: MenuItemOptionCreate,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
    _: int = Depends(verify_category_access),
):
    return await service.create_option(item_id, data)


@router.get(
    "/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}/items/{item_id}/options",
    response_model=list[MenuItemOptionResponse],
    summary="List menu item options"
)
async def list_menu_item_options(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
    _: int = Depends(verify_category_access),
):
    return await service.get_options(item_id)


@router.put(
    "/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}/items/{item_id}/options/{option_id}",
    response_model=MenuItemOptionResponse,
    summary="Update menu item option"
)
async def update_menu_item_option(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    item_id: int,
    option_id: int,
    data: MenuItemOptionUpdate,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
    _: int = Depends(verify_category_access),
):
    return await service.update_option(option_id, data, item_id)


@router.delete(
    "/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}/items/{item_id}/options/{option_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete menu item option"
)
async def delete_menu_item_option(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    item_id: int,
    option_id: int,
    current_user: User = Depends(get_current_user),
    service: MenuItemService = Depends(get_menu_item_service),
    _: int = Depends(verify_category_access),
):
    await service.delete_option(option_id, item_id)