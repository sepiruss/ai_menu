from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import get_db
from app.core.models import User
from app.modules.auth.dependencies import get_current_user, require_owner_or_admin
from app.modules.restaurants.service import RestaurantService
from app.modules.branches.schemas import BranchCreate, BranchUpdate, BranchResponse, BranchListResponse
from app.modules.branches.service import BranchService


router = APIRouter()


async def get_branch_service(db: AsyncSession = Depends(get_db)) -> BranchService:
    return BranchService(db)


async def get_restaurant_service(db: AsyncSession = Depends(get_db)) -> RestaurantService:
    return RestaurantService(db)


async def verify_restaurant_access(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    restaurant_service: RestaurantService = Depends(get_restaurant_service),
) -> int:
    """Verify user has access to restaurant and return restaurant_id"""
    if current_user.is_superuser:
        return restaurant_id
    
    has_access = await restaurant_service.check_ownership(restaurant_id, current_user.id)
    if not has_access:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Access denied to this restaurant")
    return restaurant_id


@router.post("/restaurants/{restaurant_id}/branches", response_model=BranchResponse, status_code=status.HTTP_201_CREATED, summary="Create branch")
async def create_branch(
    restaurant_id: int,
    data: BranchCreate,
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
    _: int = Depends(verify_restaurant_access),
):
    return await service.create(restaurant_id, data)


@router.get("/restaurants/{restaurant_id}/branches", response_model=BranchListResponse, summary="List branches")
async def list_branches(
    restaurant_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
    _: int = Depends(verify_restaurant_access),
):
    branches, total = await service.get_list(restaurant_id, page, page_size, is_active)
    return BranchListResponse(
        items=branches,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/restaurants/{restaurant_id}/branches/{branch_id}", response_model=BranchResponse, summary="Get branch")
async def get_branch(
    restaurant_id: int,
    branch_id: int,
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
    _: int = Depends(verify_restaurant_access),
):
    return await service.get_by_id(branch_id, restaurant_id)


@router.put("/restaurants/{restaurant_id}/branches/{branch_id}", response_model=BranchResponse, summary="Update branch")
async def update_branch(
    restaurant_id: int,
    branch_id: int,
    data: BranchUpdate,
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
    _: int = Depends(verify_restaurant_access),
):
    return await service.update(branch_id, data, restaurant_id)


@router.delete("/restaurants/{restaurant_id}/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete branch (soft)")
async def delete_branch(
    restaurant_id: int,
    branch_id: int,
    current_user: User = Depends(get_current_user),
    service: BranchService = Depends(get_branch_service),
    _: int = Depends(verify_restaurant_access),
):
    await service.delete(branch_id, restaurant_id)