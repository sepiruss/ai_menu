from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import get_db
from app.core.models import User
from app.modules.auth.dependencies import get_current_user, require_owner_or_admin
from app.modules.restaurants.service import RestaurantService
from app.modules.branches.service import BranchService
from app.modules.menus.service import MenuService
from app.modules.categories.schemas import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryListResponse, CategoryTreeResponse
from app.modules.categories.service import CategoryService


router = APIRouter()


async def get_category_service(db: AsyncSession = Depends(get_db)) -> CategoryService:
    return CategoryService(db)


async def get_restaurant_service(db: AsyncSession = Depends(get_db)) -> RestaurantService:
    return RestaurantService(db)


async def get_branch_service(db: AsyncSession = Depends(get_db)) -> BranchService:
    return BranchService(db)


async def get_menu_service(db: AsyncSession = Depends(get_db)) -> MenuService:
    return MenuService(db)


async def verify_menu_access(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    current_user: User = Depends(get_current_user),
    restaurant_service: RestaurantService = Depends(get_restaurant_service),
    branch_service: BranchService = Depends(get_branch_service),
    menu_service: MenuService = Depends(get_menu_service),
) -> int:
    """Verify user has access to restaurant, branch, and menu"""
    if current_user.is_superuser:
        return menu_id
    
    has_access = await restaurant_service.check_ownership(restaurant_id, current_user.id)
    if not has_access:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Access denied to this restaurant")
    
    branch = await branch_service.get_by_id(branch_id, restaurant_id)
    menu = await menu_service.get_by_id(menu_id, branch_id)
    return menu.id


@router.post("/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, summary="Create category")
async def create_category(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
    _: int = Depends(verify_menu_access),
):
    return await service.create(menu_id, data)


@router.get("/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories", response_model=CategoryListResponse, summary="List categories")
async def list_categories(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    parent_id: int | None = Query(None),
    is_visible: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
    _: int = Depends(verify_menu_access),
):
    categories, total = await service.get_list(menu_id, page, page_size, parent_id, is_visible)
    return CategoryListResponse(
        items=categories,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/tree", response_model=list[CategoryTreeResponse], summary="Get category tree")
async def get_category_tree(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    current_user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
    _: int = Depends(verify_menu_access),
):
    # Get all visible categories for this menu
    from sqlalchemy import select
    from app.core.models import Category
    
    result = await service.db.execute(
        select(Category).where(Category.menu_id == menu_id, Category.is_visible == True)
        .order_by(Category.display_order, Category.id)
    )
    all_categories = result.scalars().all()
    
    # Build tree manually - create dict of category data without relationship
    category_map = {}
    for cat in all_categories:
        category_map[cat.id] = CategoryTreeResponse(
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
    
    root_categories = []
    for cat in all_categories:
        cat_resp = category_map[cat.id]
        if cat.parent_id is None:
            root_categories.append(cat_resp)
        else:
            parent = category_map.get(cat.parent_id)
            if parent:
                parent.children.append(cat_resp)
    
    return root_categories


@router.get("/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}", response_model=CategoryResponse, summary="Get category")
async def get_category(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    current_user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
    _: int = Depends(verify_menu_access),
):
    return await service.get_by_id(category_id, menu_id)


@router.put("/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}", response_model=CategoryResponse, summary="Update category")
async def update_category(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
    _: int = Depends(verify_menu_access),
):
    return await service.update(category_id, data, menu_id)


@router.delete("/restaurants/{restaurant_id}/branches/{branch_id}/menus/{menu_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete category")
async def delete_category(
    restaurant_id: int,
    branch_id: int,
    menu_id: int,
    category_id: int,
    current_user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
    _: int = Depends(verify_menu_access),
):
    await service.delete(category_id, menu_id)