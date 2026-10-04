from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import get_db
from app.core.models import User
from app.modules.auth.dependencies import get_current_user, require_owner_or_admin
from app.modules.restaurants.schemas import (
    RestaurantCreate,
    RestaurantUpdate,
    RestaurantResponse,
    RestaurantListResponse,
)
from app.modules.restaurants.service import RestaurantService


router = APIRouter()


async def get_restaurant_service(db: AsyncSession = Depends(get_db)) -> RestaurantService:
    return RestaurantService(db)


@router.post("/restaurants", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED, summary="Create restaurant")
async def create_restaurant(
    data: RestaurantCreate,
    current_user: User = Depends(require_owner_or_admin),
    service: RestaurantService = Depends(get_restaurant_service),
):
    return await service.create(data, current_user)


@router.get("/restaurants", response_model=RestaurantListResponse, summary="List restaurants")
async def list_restaurants(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    current_user: User = Depends(require_owner_or_admin),
    service: RestaurantService = Depends(get_restaurant_service),
):
    # Non-superusers can only see their own restaurants
    owner_id = None if current_user.is_superuser else current_user.id
    restaurants, total = await service.get_list(owner_id=owner_id, page=page, page_size=page_size, is_active=is_active)
    
    return RestaurantListResponse(
        items=restaurants,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/restaurants/{restaurant_id}", response_model=RestaurantResponse, summary="Get restaurant")
async def get_restaurant(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    service: RestaurantService = Depends(get_restaurant_service),
):
    owner_id = None if current_user.is_superuser else current_user.id
    return await service.get_by_id(restaurant_id, owner_id)


@router.put("/restaurants/{restaurant_id}", response_model=RestaurantResponse, summary="Update restaurant")
async def update_restaurant(
    restaurant_id: int,
    data: RestaurantUpdate,
    current_user: User = Depends(get_current_user),
    service: RestaurantService = Depends(get_restaurant_service),
):
    owner_id = None if current_user.is_superuser else current_user.id
    return await service.update(restaurant_id, data, owner_id)


@router.delete("/restaurants/{restaurant_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete restaurant (soft)")
async def delete_restaurant(
    restaurant_id: int,
    current_user: User = Depends(get_current_user),
    service: RestaurantService = Depends(get_restaurant_service),
):
    owner_id = None if current_user.is_superuser else current_user.id
    await service.delete(restaurant_id, owner_id)