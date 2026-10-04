from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import NotFoundException, ConflictException, ForbiddenException
from app.core.models import Restaurant, Branch
from app.modules.branches.schemas import BranchCreate, BranchUpdate


class BranchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, restaurant_id: int, data: BranchCreate) -> Branch:
        # Verify restaurant exists
        restaurant = await self.db.get(Restaurant, restaurant_id)
        if not restaurant:
            raise NotFoundException("Restaurant", restaurant_id)
        
        # Check code uniqueness
        result = await self.db.execute(select(Branch).where(Branch.code == data.code))
        if result.scalar_one_or_none():
            raise ConflictException("branch", "Code already in use")
        
        branch = Branch(
            restaurant_id=restaurant_id,
            name=data.name,
            code=data.code,
            address=data.address,
            phone=data.phone,
            latitude=data.latitude,
            longitude=data.longitude,
            settings=data.settings,
            operating_hours=data.operating_hours,
        )
        self.db.add(branch)
        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    async def get_by_id(self, branch_id: int, restaurant_id: int | None = None) -> Branch:
        query = select(Branch).where(Branch.id == branch_id)
        if restaurant_id is not None:
            query = query.where(Branch.restaurant_id == restaurant_id)
        
        result = await self.db.execute(query)
        branch = result.scalar_one_or_none()
        if not branch:
            raise NotFoundException("Branch", branch_id)
        return branch

    async def get_list(
        self,
        restaurant_id: int,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[Branch], int]:
        query = select(Branch).where(Branch.restaurant_id == restaurant_id)
        
        if is_active is not None:
            query = query.where(Branch.is_active == is_active)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Branch.created_at.desc())
        result = await self.db.execute(query)
        branches = result.scalars().all()
        
        return list(branches), total

    async def update(self, branch_id: int, data: BranchUpdate, restaurant_id: int | None = None) -> Branch:
        branch = await self.get_by_id(branch_id, restaurant_id)
        
        if data.code is not None and data.code != branch.code:
            result = await self.db.execute(
                select(Branch).where(Branch.code == data.code, Branch.id != branch_id)
            )
            if result.scalar_one_or_none():
                raise ConflictException("branch", "Code already in use")
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(branch, field, value)
        
        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    async def delete(self, branch_id: int, restaurant_id: int | None = None) -> None:
        branch = await self.get_by_id(branch_id, restaurant_id)
        branch.is_active = False
        await self.db.commit()