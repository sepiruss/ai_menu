from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import get_db
from app.core.models import User
from app.modules.auth.dependencies import get_current_user, require_owner_or_admin
from app.modules.restaurants.service import RestaurantService
from app.modules.branches.service import BranchService
from app.modules.menus.schemas import MenuCreate, MenuUpdate, MenuResponse, MenuListResponse
from app.modules.menus.service import MenuService


router = APIRouter()


async def get_menu_service(db: AsyncSession = Depends(get_db)) -> MenuService:
    return MenuService(db)


async def get_restaurant_service(db: AsyncSession = Depends(get_db)) -> RestaurantService:
    return RestaurantService(db)


async def get_branch_service(db: AsyncSession = Depends(get_db)) -> BranchService:
    return BranchService(db)


async def verify_branch_access(
    restaurant_id: int,
    branch_id: int,
    current_user: User = Depends(get_current_user),
    restaurant_service: RestaurantService = Depends(get_restaurant_service),
    branch_service: BranchService = Depends(get_branch_service),
) -> int:
    """Verify user has access to restaurant and branch"""
    if current_user.is_superuser:
        return branch_id
    
    has_access = await restaurant_service.check_ownership(restaurant_id, current_user.id)
    if not has_access:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Access denied to this restaurant")
    
    # Verify branch belongs to restaurant
    branch = await branch_service.get_by_id(branch_id, restaurant_id)
    return branch.id


@router.post("/restaurants/{restaurant_id}/branches/{branch_id}/menus", response_model=MenuResponse, status_code=status.HTTP_201_CREATED, summary="Create menu")
async def create_menu(
    restaurant_id: int,
    branch_id: int,
    data: MenuCreate,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
    _: int = Depends(verify_branch_access),
):
    return await service.create(branch_id, data)


@router.get("/restaurants/{restaurant_id}/branches/{branch_id}/menus", response_model=MenuListResponse, summary="List menus")
async def list_menus(
    restaurant_id: int,
    branch_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
    _: int = Depends(verify_branch_access),
):
    menus, total = await service.get_list(branch_id, page, page_size, is_active)
    return MenuListResponse(
        items=menus,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}", response_model=MenuResponse, summary="Get menu")
async def get_menu(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
    _: int = Depends(verify_branch_access),
):
    return await service.get_by_id(menu_id, branch_id)


@router.put("/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}", response_model=MenuResponse, summary="Update menu")
async def update_menu(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    data: MenuUpdate,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
    _: int = Depends(verify_branch_access),
):
    return await service.update(menu_id, data, branch_id)


@router.delete("/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete menu (soft)")
async def delete_menu(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    current_user: User = Depends(get_current_user),
    service: MenuService = Depends(get_menu_service),
    _: int = Depends(verify_branch_access),
):
    await service.delete(menu_id, branch_id)