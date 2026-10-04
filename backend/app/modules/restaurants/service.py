from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.exceptions import NotFoundException, ConflictException, ForbiddenException
from app.core.models import Restaurant, User
from app.modules.restaurants.schemas import RestaurantCreate, RestaurantUpdate


class RestaurantService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: RestaurantCreate, owner: User) -> Restaurant:
        # Check slug uniqueness
        result = await self.db.execute(select(Restaurant).where(Restaurant.slug == data.slug))
        if result.scalar_one_or_none():
            raise ConflictException("restaurant", "Slug already in use")
        
        restaurant = Restaurant(
            name=data.name,
            slug=data.slug,
            description=data.description,
            timezone=data.timezone,
            settings=data.settings,
            branding=data.branding,
            owner_id=owner.id,
        )
        self.db.add(restaurant)
        await self.db.commit()
        await self.db.refresh(restaurant)
        return restaurant

    async def get_by_id(self, restaurant_id: int, owner_id: int | None = None) -> Restaurant:
        query = select(Restaurant).where(Restaurant.id == restaurant_id)
        if owner_id is not None:
            query = query.where(Restaurant.owner_id == owner_id)
        
        result = await self.db.execute(query)
        restaurant = result.scalar_one_or_none()
        if not restaurant:
            raise NotFoundException("Restaurant", restaurant_id)
        return restaurant

    async def get_list(
        self,
        owner_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[Restaurant], int]:
        query = select(Restaurant)
        
        if owner_id is not None:
            query = query.where(Restaurant.owner_id == owner_id)
        if is_active is not None:
            query = query.where(Restaurant.is_active == is_active)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Restaurant.created_at.desc())
        result = await self.db.execute(query)
        restaurants = result.scalars().all()
        
        return list(restaurants), total

    async def update(self, restaurant_id: int, data: RestaurantUpdate, owner_id: int | None = None) -> Restaurant:
        restaurant = await self.get_by_id(restaurant_id, owner_id)
        
        if data.slug is not None and data.slug != restaurant.slug:
            result = await self.db.execute(
                select(Restaurant).where(Restaurant.slug == data.slug, Restaurant.id != restaurant_id)
            )
            if result.scalar_one_or_none():
                raise ConflictException("restaurant", "Slug already in use")
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(restaurant, field, value)
        
        await self.db.commit()
        await self.db.refresh(restaurant)
        return restaurant

    async def delete(self, restaurant_id: int, owner_id: int | None = None) -> None:
        restaurant = await self.get_by_id(restaurant_id, owner_id)
        restaurant.is_active = False
        await self.db.commit()

    async def check_ownership(self, restaurant_id: int, user_id: int) -> bool:
        result = await self.db.execute(
            select(Restaurant).where(Restaurant.id == restaurant_id, Restaurant.owner_id == user_id)
        )
        return result.scalar_one_or_none() is not None