import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from app.main import create_app
from app.core.database import Base, get_db
from app.core.config import get_settings
from app.core.security import hash_password, create_access_token
from app.core.models import User
from app.core.models import CustomerEvent, CustomerEventType
from app.core.models import Restaurant, Branch, Table, Menu, Category, MenuItem

# Test database URL (uses file-based SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_phase3.db"


def create_test_engine():
    """Create a new test engine each time to avoid index issues."""
    return create_async_engine("sqlite+aiosqlite:///./test_phase3.db", echo=False, poolclass=NullPool)


def cleanup_test_db():
    """Remove the test database file if it exists."""
    import os
    if os.path.exists("./test_phase3.db"):
        try:
            os.remove("./test_phase3.db")
        except OSError:
            pass


# Global flag to track if tables have been created
_tables_created = False


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create tables once per test session."""
    global _tables_created
    # Clean up any existing test database
    import os
    if os.path.exists("./test_phase3.db"):
        try:
            os.remove("./test_phase3.db")
        except OSError:
            pass
    
    # Create new engine and tables
    test_engine = create_test_engine()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _tables_created = True
    yield
    # Clean up test database file after all tests
    if os.path.exists("./test_phase3.db"):
        try:
            os.remove("./test_phase3.db")
        except OSError:
            pass


@pytest_asyncio.fixture
async def test_engine():
    """Create a test engine for the session."""
    return create_test_engine()


@pytest_asyncio.fixture
async def db(test_engine) -> AsyncSession:
    """Create a new database session for each test."""
    TestAsyncSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with TestAsyncSessionLocal() as session:
        yield session
        # Clean up all tables after each test
        await session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f"DELETE FROM {table.name}"))
        await session.commit()


@pytest_asyncio.fixture
async def app(test_engine):
    """Create a test FastAPI app with test database."""
    app = create_app()
    
    # Override get_db dependency to use test database
    TestAsyncSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async def override_get_db():
        async with TestAsyncSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> AsyncClient:
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    """Create a test superuser."""
    user = User(
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        role="superuser",
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_owner(db: AsyncSession) -> User:
    """Create a test owner (non-superuser)."""
    user = User(
        email="owner@example.com",
        password_hash=hash_password("ownerpassword123"),
        role="owner",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def owner_headers(test_owner: User) -> dict:
    """Create auth headers for test owner."""
    token = create_access_token(data={"sub": str(test_owner.id), "email": test_owner.email, "role": test_owner.role})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_restaurant(db: AsyncSession, test_user: User) -> Restaurant:
    """Create a test restaurant."""
    restaurant = Restaurant(
        name="Test Restaurant",
        slug="test-restaurant",
        owner_id=test_user.id,
        is_active=True,
    )
    db.add(restaurant)
    await db.commit()
    await db.refresh(restaurant)
    return restaurant


@pytest_asyncio.fixture
async def test_branch(db: AsyncSession, test_restaurant: Restaurant) -> Branch:
    """Create a test branch."""
    branch = Branch(
        restaurant_id=test_restaurant.id,
        name="Test Branch",
        code="TEST",
        is_active=True,
    )
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch


@pytest_asyncio.fixture
async def test_table(db: AsyncSession, test_branch: Branch) -> Table:
    """Create a test table."""
    table = Table(
        branch_id=test_branch.id,
        name="Table 1",
        code="T1",
        capacity=4,
        is_active=True,
    )
    db.add(table)
    await db.commit()
    await db.refresh(table)
    return table


@pytest_asyncio.fixture
async def test_menu(db: AsyncSession, test_branch: Branch) -> Menu:
    """Create a test menu."""
    menu = Menu(
        branch_id=test_branch.id,
        name="Test Menu",
        description="Test menu description",
        is_active=True,
        is_default=True,
    )
    db.add(menu)
    await db.commit()
    await db.refresh(menu)
    return menu


@pytest_asyncio.fixture
async def test_category(db: AsyncSession, test_menu: Menu) -> Category:
    """Create a test category."""
    category = Category(
        menu_id=test_menu.id,
        name="Test Category",
        slug="test-category",
        display_order=1,
        is_visible=True,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@pytest_asyncio.fixture
async def test_menu_item(db: AsyncSession, test_category: Category) -> MenuItem:
    """Create a test menu item."""
    menu_item = MenuItem(
        category_id=test_category.id,
        name="Test Item",
        description="Test item description",
        price_toman=50000,
        price_rial=500000,
        is_available=True,
        is_popular=False,
        is_new=False,
        display_order=1,
    )
    db.add(menu_item)
    await db.commit()
    await db.refresh(menu_item)
    return menu_item


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create auth headers for test user."""
    token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email, "role": test_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def superuser_headers(test_user: User) -> dict:
    """Create auth headers for superuser."""
    token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email, "role": test_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def settings():
    """Get test settings."""
    return get_settings()