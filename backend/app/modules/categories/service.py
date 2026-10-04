from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ConflictException
from app.core.models import Menu, Category
from app.modules.categories.schemas import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, menu_id: int, data: CategoryCreate) -> Category:
        # Verify menu exists
        menu = await self.db.get(Menu, menu_id)
        if not menu:
            raise NotFoundException("Menu", menu_id)
        
        # Verify parent exists if provided
        if data.parent_id is not None:
            parent = await self.db.get(Category, data.parent_id)
            if not parent or parent.menu_id != menu_id:
                raise NotFoundException("Parent category", data.parent_id)
        
        category = Category(
            menu_id=menu_id,
            name=data.name,
            slug=data.slug,
            parent_id=data.parent_id,
            display_order=data.display_order,
            is_visible=data.is_visible,
            translation=data.translation,
        )
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def get_by_id(self, category_id: int, menu_id: int | None = None) -> Category:
        query = select(Category).where(Category.id == category_id)
        if menu_id is not None:
            query = query.where(Category.menu_id == menu_id)
        
        result = await self.db.execute(query)
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundException("Category", category_id)
        return category

    async def get_list(
        self,
        menu_id: int,
        page: int = 1,
        page_size: int = 20,
        parent_id: int | None = None,
        is_visible: bool | None = None,
    ) -> tuple[list[Category], int]:
        query = select(Category).where(Category.menu_id == menu_id)
        
        if parent_id == 0:  # Special value for root categories
            query = query.where(Category.parent_id.is_(None))
        elif parent_id is not None:
            query = query.where(Category.parent_id == parent_id)
        
        if is_visible is not None:
            query = query.where(Category.is_visible == is_visible)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Category.display_order, Category.id)
        result = await self.db.execute(query)
        categories = result.scalars().all()
        
        return list(categories), total

    async def get_tree(self, menu_id: int, parent_id: int | None = None) -> list[Category]:
        """Get category hierarchy as flat list, then build tree in API"""
        query = select(Category).where(Category.menu_id == menu_id, Category.is_visible == True)
        if parent_id is not None:
            query = query.where(Category.parent_id == parent_id)
        else:
            query = query.where(Category.parent_id.is_(None))
        
        query = query.order_by(Category.display_order, Category.id)
        result = await self.db.execute(query)
        categories = result.scalars().all()
        return list(categories)

    async def update(self, category_id: int, data: CategoryUpdate, menu_id: int | None = None) -> Category:
        category = await self.get_by_id(category_id, menu_id)
        
        update_data = data.model_dump(exclude_unset=True)
        
        # Verify parent if changing
        if "parent_id" in update_data and update_data["parent_id"] is not None:
            if update_data["parent_id"] == category_id:
                from app.core.exceptions import ValidationException
                raise ValidationException("Category cannot be its own parent")
            
            parent = await self.db.get(Category, update_data["parent_id"])
            if not parent or (menu_id and parent.menu_id != menu_id):
                raise NotFoundException("Parent category", update_data["parent_id"])
        
        for field, value in update_data.items():
            setattr(category, field, value)
        
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete(self, category_id: int, menu_id: int | None = None) -> None:
        category = await self.get_by_id(category_id, menu_id)
        
        # Check for children
        result = await self.db.execute(select(Category).where(Category.parent_id == category_id))
        if result.scalar_one_or_none():
            from app.core.exceptions import ConflictException
            raise ConflictException("category", "Cannot delete category with children. Move or delete children first.")
        
        # Check for menu items
        result = await self.db.execute(select(Category).where(Category.id == category_id))
        # Menu items are in MenuItem model - check via relationship
        from app.core.models import MenuItem
        result = await self.db.execute(select(MenuItem).where(MenuItem.category_id == category_id))
        if result.scalar_one_or_none():
            from app.core.exceptions import ConflictException
            raise ConflictException("category", "Cannot delete category with menu items. Move or delete items first.")
        
        await self.db.delete(category)
        await self.db.commit()