from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from decimal import Decimal
from app.core.exceptions import NotFoundException, ConflictException
from app.core.models import Category, MenuItem, MenuItemOption
from app.modules.menu_items.schemas import MenuItemCreate, MenuItemUpdate, MenuItemOptionCreate, MenuItemOptionUpdate


class MenuItemService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, category_id: int, data: MenuItemCreate) -> MenuItem:
        # Verify category exists
        category = await self.db.get(Category, category_id)
        if not category:
            from app.core.exceptions import NotFoundException
            raise NotFoundException("Category", category_id)
        
        menu_item = MenuItem(
            category_id=category_id,
            name=data.name,
            description=data.description,
            price_toman=data.price_toman,
            price_rial=data.price_rial,
            is_available=data.is_available,
            is_popular=data.is_popular,
            is_new=data.is_new,
            display_order=data.display_order,
            image_url=data.image_url,
            item_metadata=data.item_metadata,
            allergens_tags=data.allergens_tags,
        )
        self.db.add(menu_item)
        await self.db.commit()
        await self.db.refresh(menu_item)
        return menu_item

    async def get_by_id(self, item_id: int, category_id: int | None = None) -> MenuItem:
        query = select(MenuItem).options(selectinload(MenuItem.options)).where(MenuItem.id == item_id)
        if category_id is not None:
            query = query.where(MenuItem.category_id == category_id)
        
        result = await self.db.execute(query)
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundException("MenuItem", item_id)
        return item

    async def get_list(
        self,
        category_id: int,
        page: int = 1,
        page_size: int = 20,
        is_available: bool | None = None,
        is_popular: bool | None = None,
        is_new: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[MenuItem], int]:
        query = select(MenuItem).options(selectinload(MenuItem.options)).where(MenuItem.category_id == category_id)
        
        if is_available is not None:
            query = query.where(MenuItem.is_available == is_available)
        if is_popular is not None:
            query = query.where(MenuItem.is_popular == is_popular)
        if is_new is not None:
            query = query.where(MenuItem.is_new == is_new)
        if search:
            query = query.where(MenuItem.name.ilike(f"%{search}%"))
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(MenuItem.display_order, MenuItem.id)
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total

    async def update(self, item_id: int, data: MenuItemUpdate, category_id: int | None = None) -> MenuItem:
        item = await self.get_by_id(item_id, category_id)
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, item_id: int, category_id: int | None = None) -> None:
        item = await self.get_by_id(item_id, category_id)
        item.is_available = False  # Soft delete
        await self.db.commit()

    # Options
    async def create_option(self, menu_item_id: int, data: MenuItemOptionCreate) -> MenuItemOption:
        menu_item = await self.db.get(MenuItem, menu_item_id)
        if not menu_item:
            raise NotFoundException("MenuItem", menu_item_id)
        
        option = MenuItemOption(
            menu_item_id=menu_item_id,
            name=data.name,
            price_adjustment_toman=data.price_adjustment_toman,
            price_adjustment_rial=data.price_adjustment_rial,
            is_required=data.is_required,
            display_order=data.display_order,
            options_config=data.options_config,
        )
        self.db.add(option)
        await self.db.commit()
        await self.db.refresh(option)
        return option

    async def get_option(self, option_id: int, menu_item_id: int | None = None) -> MenuItemOption:
        query = select(MenuItemOption).where(MenuItemOption.id == option_id)
        if menu_item_id is not None:
            query = query.where(MenuItemOption.menu_item_id == menu_item_id)
        
        result = await self.db.execute(query)
        option = result.scalar_one_or_none()
        if not option:
            raise NotFoundException("MenuItemOption", option_id)
        return option

    async def update_option(self, option_id: int, data: MenuItemOptionUpdate, menu_item_id: int | None = None) -> MenuItemOption:
        option = await self.get_option(option_id, menu_item_id)
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(option, field, value)
        
        await self.db.commit()
        await self.db.refresh(option)
        return option

    async def delete_option(self, option_id: int, menu_item_id: int | None = None) -> None:
        option = await self.get_option(option_id, menu_item_id)
        await self.db.delete(option)
        await self.db.commit()

    async def get_options(self, menu_item_id: int) -> list[MenuItemOption]:
        result = await self.db.execute(
            select(MenuItemOption)
            .where(MenuItemOption.menu_item_id == menu_item_id)
            .order_by(MenuItemOption.display_order)
        )
        return list(result.scalars().all())