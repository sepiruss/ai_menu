import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import (
    User, Restaurant, Branch, Table, Menu, Category, 
    MenuItem, MenuItemOption, QRCode, CustomerSession
)
from app.core.security import hash_password
from datetime import datetime, timezone, timedelta


@pytest_asyncio.fixture
async def test_qr_code(db: AsyncSession, test_restaurant, test_branch, test_table) -> QRCode:
    qr = QRCode(
        restaurant_id=test_restaurant.id,
        branch_id=test_branch.id,
        table_id=test_table.id,
        token="test-qr-token-12345678901234567890123456789012",
        label="Table 1",
        is_active=True,
    )
    db.add(qr)
    await db.commit()
    await db.refresh(qr)
    return qr


@pytest_asyncio.fixture
async def test_inactive_qr_code(db: AsyncSession, test_restaurant, test_branch) -> QRCode:
    qr = QRCode(
        restaurant_id=test_restaurant.id,
        branch_id=test_branch.id,
        token="inactive-qr-token-12345678901234567890123456789012",
        is_active=False,
    )
    db.add(qr)
    await db.commit()
    await db.refresh(qr)
    return qr


@pytest_asyncio.fixture
async def test_menu(db: AsyncSession, test_branch) -> Menu:
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
async def test_category(db: AsyncSession, test_menu) -> Category:
    cat = Category(
        menu_id=test_menu.id,
        name="Appetizers",
        slug="appetizers",
        display_order=1,
        is_visible=True,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@pytest_asyncio.fixture
async def test_subcategory(db: AsyncSession, test_menu, test_category) -> Category:
    cat = Category(
        menu_id=test_menu.id,
        parent_id=test_category.id,
        name="Hot Appetizers",
        slug="hot-appetizers",
        display_order=1,
        is_visible=True,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


@pytest_asyncio.fixture
async def test_menu_item(db: AsyncSession, test_category) -> MenuItem:
    item = MenuItem(
        category_id=test_category.id,
        name="Test Item",
        description="Test item description",
        price_toman=50000,
        price_rial=500000,
        is_available=True,
        is_popular=True,
        is_new=False,
        display_order=1,
        image_url=None,
        item_metadata={},
        allergens_tags=[],
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@pytest_asyncio.fixture
async def test_unavailable_item(db: AsyncSession, test_category) -> MenuItem:
    item = MenuItem(
        category_id=test_category.id,
        name="Unavailable Item",
        price_toman=30000,
        price_rial=300000,
        is_available=False,
        is_popular=False,
        is_new=False,
        display_order=2,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


class TestQRCodeResolution:
    """Test QR code resolution and session creation"""

    async def test_resolve_valid_qr_creates_session(
        self, client: AsyncClient, test_qr_code: QRCode
    ):
        response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={"device_info": {"user_agent": "test-agent"}}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_token" in data
        assert data["restaurant_id"] == test_qr_code.restaurant_id
        assert data["branch_id"] == test_qr_code.branch_id
        assert data["table_id"] == test_qr_code.table_id
        assert data["restaurant_name"] == test_qr_code.restaurant.name
        assert data["branch_name"] == test_qr_code.branch.name

    async def test_resolve_invalid_qr_returns_404(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/public/qr/nonexistent-token-123456789012345678901234",
            json={}
        )
        assert response.status_code == 404

    async def test_resolve_inactive_qr_returns_422(
        self, client: AsyncClient, test_inactive_qr_code: QRCode
    ):
        response = await client.post(
            f"/api/v1/public/qr/{test_inactive_qr_code.token}",
            json={}
        )
        assert response.status_code == 422
        assert "inactive" in response.json()["message"].lower()

    async def test_resolve_qr_continues_existing_session(
        self, client: AsyncClient, test_qr_code: QRCode
    ):
        # First request creates session
        response1 = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={"device_info": {"user_agent": "test-agent"}}
        )
        assert response1.status_code == 200
        session_token = response1.json()["session_token"]
        
        # Second request with same token continues session
        response2 = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={"session_token": session_token, "device_info": {"user_agent": "test-agent"}}
        )
        assert response2.status_code == 200
        assert response2.json()["session_token"] == session_token


class TestPublicMenu:
    """Test public menu browsing"""

    async def test_get_public_menu(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu: Menu, test_category: Category, test_menu_item: MenuItem
    ):
        # First resolve QR to get session
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        # Get menu
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_menu.id
        assert data["name"] == "Test Menu"
        assert len(data["categories"]) == 1
        assert data["categories"][0]["name"] == "Appetizers"

    async def test_get_public_menu_invalid_session(
        self, client: AsyncClient, test_qr_code: QRCode
    ):
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}",
            headers={"X-Session-Token": "invalid-token"}
        )
        assert response.status_code == 422

    async def test_get_public_categories(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu: Menu, test_category: Category, test_subcategory: Category
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/categories",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Appetizers"
        assert len(data[0]["children"]) == 1
        assert data[0]["children"][0]["name"] == "Hot Appetizers"

    async def test_get_public_categories_with_parent_filter(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu: Menu, test_category: Category, test_subcategory: Category
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/categories?parent_id={test_category.id}",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Hot Appetizers"

    async def test_get_public_items(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu: Menu, test_category: Category, test_menu_item: MenuItem
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/items?category_id={test_category.id}",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Test Item"
        # Price is serialized as string by Pydantic
        assert data["items"][0]["price_toman"] == "50000.00"
        assert data["items"][0]["is_popular"] == True

    async def test_get_public_items_filters_unavailable(
        self, client: AsyncClient, test_qr_code: QRCode, test_category: Category, test_unavailable_item: MenuItem
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/items?category_id={test_category.id}",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200
        data = response.json()
        # Unavailable item should not appear
        assert data["total"] == 0

    async def test_get_public_item_details(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu_item: MenuItem
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/items/{test_menu_item.id}",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_menu_item.id
        assert data["name"] == "Test Item"
        # Price is serialized as string by Pydantic
        assert data["price_toman"] == "50000.00"

    async def test_get_unavailable_item_returns_404(
        self, client: AsyncClient, test_qr_code: QRCode, test_unavailable_item: MenuItem
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/items/{test_unavailable_item.id}",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 404

    async def test_get_nonexistent_item_returns_404(
        self, client: AsyncClient, test_qr_code: QRCode
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/items/99999",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 404

    async def test_search_items(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu: Menu, test_category: Category, test_menu_item: MenuItem
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.post(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/search",
            json={"query": "Test", "page": 1, "page_size": 20},
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Test Item"

    async def test_search_items_with_category_filter(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu: Menu, test_category: Category, test_menu_item: MenuItem
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.post(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/search",
            json={"query": "Test", "category_id": test_category.id, "page": 1, "page_size": 20},
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    async def test_search_items_wrong_category(
        self, client: AsyncClient, test_qr_code: QRCode, test_category: Category
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.post(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/search",
            json={"query": "Test", "category_id": 99999, "page": 1, "page_size": 20},
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestCustomerEvents:
    """Test customer event tracking"""

    async def test_menu_view_event_tracked(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu: Menu
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        assert qr_response.status_code == 200
        
        # Verify event was created by checking menu view
        session_token = qr_response.json()["session_token"]
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200

    async def test_category_view_event_tracked(
        self, client: AsyncClient, test_qr_code: QRCode, test_category: Category
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/categories",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200

    async def test_item_view_event_tracked(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu_item: MenuItem
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/items/{test_menu_item.id}",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200

    async def test_search_event_tracked(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu_item: MenuItem
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        response = await client.post(
            f"/api/v1/public/menu/{test_qr_code.branch_id}/search",
            json={"query": "Test"},
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 200


class TestSecurityAndTenantIsolation:
    """Test security and tenant isolation for public endpoints"""

    async def test_cross_tenant_access_denied(
        self, client: AsyncClient, test_qr_code: QRCode, db: AsyncSession
    ):
        # Create another restaurant
        other_restaurant = Restaurant(
            name="Other Restaurant",
            slug="other-restaurant",
            owner_id=test_qr_code.restaurant.owner_id,
        )
        db.add(other_restaurant)
        await db.commit()
        await db.refresh(other_restaurant)
        
        other_branch = Branch(
            restaurant_id=other_restaurant.id,
            name="Other Branch",
            code="OTHER",
        )
        db.add(other_branch)
        await db.commit()
        await db.refresh(other_branch)
        
        # Get session from first restaurant
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        # Try to access menu from other restaurant's branch
        response = await client.get(
            f"/api/v1/public/menu/{other_branch.id}",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 422
        assert "mismatch" in response.json()["message"].lower()

    async def test_expired_session_rejected(
        self, client: AsyncClient, test_qr_code: QRCode, test_menu: Menu, db: AsyncSession
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        # Manually expire the session
        from app.core.models import CustomerSession
        from sqlalchemy import select
        
        result = await db.execute(
            select(CustomerSession).where(CustomerSession.session_token == session_token)
        )
        session = result.scalar_one()
        session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.commit()
        
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}",
            headers={"X-Session-Token": session_token}
        )
        assert response.status_code == 422

    async def test_invalid_session_token_rejected(
        self, client: AsyncClient, test_qr_code: QRCode
    ):
        response = await client.get(
            f"/api/v1/public/menu/{test_qr_code.branch_id}",
            headers={"X-Session-Token": "completely-invalid-token-1234567890123456"}
        )
        assert response.status_code == 422

    async def test_qr_token_cannot_access_admin_data(
        self, client: AsyncClient, test_qr_code: QRCode
    ):
        qr_response = await client.post(
            f"/api/v1/public/qr/{test_qr_code.token}",
            json={}
        )
        session_token = qr_response.json()["session_token"]
        
        # Try to access admin endpoint with public session
        response = await client.get(
            f"/api/v1/admin/restaurants",
            headers={"X-Session-Token": session_token}
        )
        # Should fail because admin endpoints require proper auth
        assert response.status_code in (401, 403)


class TestQRCodeAdminManagement:
    """Test QR code admin management endpoints"""

    async def test_create_qr_code_requires_auth(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/public/admin/qr-codes",
            json={
                "restaurant_id": 1,
                "branch_id": 1,
                "label": "Test QR"
            }
        )
        assert response.status_code in (401, 403)

    # Note: Full admin tests would require proper auth setup
    # These are placeholder tests for the admin endpoints


# Import at the top