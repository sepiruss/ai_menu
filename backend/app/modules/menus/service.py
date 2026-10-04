from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ConflictException
from app.core.models import Branch, Menu
from app.modules.menus.schemas import MenuCreate, MenuUpdate


class MenuService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, branch_id: int, data: MenuCreate) -> Menu:
        # Verify branch exists
        branch = await self.db.get(Branch, branch_id)
        if not branch:
            from app.core.exceptions import NotFoundException
            raise NotFoundException("Branch", branch_id)
        
        # If setting as default, unset other defaults
        if data.is_default:
            await self.db.execute(
                select(Menu).where(Menu.branch_id == branch_id, Menu.is_default == True)
            )
            # We'll handle this in update
        
        menu = Menu(
            branch_id=branch_id,
            name=data.name,
            description=data.description,
            is_active=data.is_active,
            is_default=data.is_default,
            branding=data.branding,
        )
        self.db.add(menu)
        await self.db.commit()
        await self.db.refresh(menu)
        
        # If this is default, unset others
        if menu.is_default:
            await self._unset_other_defaults(branch_id, menu.id)
        
        return menu

    async def _unset_other_defaults(self, branch_id: int, exclude_id: int) -> None:
        result = await self.db.execute(
            select(Menu).where(Menu.branch_id == branch_id, Menu.id != exclude_id, Menu.is_default == True)
        )
        for menu in result.scalars().all():
            menu.is_default = False
        await self.db.commit()

    async def get_by_id(self, menu_id: int, branch_id: int | None = None) -> Menu:
        query = select(Menu).where(Menu.id == menu_id)
        if branch_id is not None:
            query = query.where(Menu.branch_id == branch_id)
        
        result = await self.db.execute(query)
        menu = result.scalar_one_or_none()
        if not menu:
            raise NotFoundException("Menu", menu_id)
        return menu

    async def get_list(
        self,
        branch_id: int,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[Menu], int]:
        query = select(Menu).where(Menu.branch_id == branch_id)
        
        if is_active is not None:
            query = query.where(Menu.is_active == is_active)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Menu.created_at.desc())
        result = await self.db.execute(query)
        menus = result.scalars().all()
        
        return list(menus), total

    async def update(self, menu_id: int, data: MenuUpdate, branch_id: int | None = None) -> Menu:
        menu = await self.get_by_id(menu_id, branch_id)
        
        update_data = data.model_dump(exclude_unset=True)
        
        # Handle default flag
        if update_data.get("is_default") is True and not menu.is_default:
            await self._unset_other_defaults(menu.branch_id, menu_id)
        
        for field, value in update_data.items():
            setattr(menu, field, value)
        
        await self.db.commit()
        await self.db.refresh(menu)
        return menu

    async def delete(self, menu_id: int, branch_id: int | None = None) -> None:
        menu = await self.get_by_id(menu_id, branch_id)
        menu.is_active = False
        await self.db.commit()

    async def get_default(self, branch_id: int) -> Menu | None:
        result = await self.db.execute(
            select(Menu).where(Menu.branch_id == branch_id, Menu.is_default == True, Menu.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_active_menus(self, branch_id: int) -> list[Menu]:
        result = await self.db.execute(
            select(Menu).where(Menu.branch_id == branch_id, Menu.is_active == True).order_by(Menu.is_default.desc())
        )
        return list(result.scalars().all())