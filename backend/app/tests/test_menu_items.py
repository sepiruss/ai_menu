import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.models import User, Restaurant, Branch, Menu, Category, MenuItem, MenuItemOption
from app.core.security import create_access_token


class TestMenuItems:
    async def test_create_menu_item(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, test_category: Category):
        response = await client.post(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items",
            json={
                "name": "Caesar Salad",
                "description": "Fresh romaine lettuce with caesar dressing",
                "price_toman": "50000",
                "price_rial": "500000",
                "is_available": True,
                "is_popular": True,
                "is_new": False,
                "display_order": 1,
                "allergens_tags": ["dairy", "gluten"]
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Caesar Salad"
        assert data["price_toman"] == "50000.00"
        assert data["price_rial"] == "500000.00"
        assert data["is_popular"] is True
        assert data["allergens_tags"] == ["dairy", "gluten"]

    async def test_list_menu_items(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, test_category: Category, db: AsyncSession):
        for i in range(3):
            item = MenuItem(id=i+1, category_id=test_category.id, name=f"Item {i}", price_toman=Decimal("10000"), price_rial=Decimal("100000"), display_order=i)
            db.add(item)
        await db.commit()
        
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    async def test_list_menu_items_filters(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, test_category: Category, db: AsyncSession):
        item1 = MenuItem(id=1, category_id=test_category.id, name="Available Item", price_toman=Decimal("10000"), price_rial=Decimal("100000"), is_available=True, is_popular=False, is_new=False)
        item2 = MenuItem(id=2, category_id=test_category.id, name="Popular Item", price_toman=Decimal("20000"), price_rial=Decimal("200000"), is_available=True, is_popular=True, is_new=False)
        item3 = MenuItem(id=3, category_id=test_category.id, name="New Item", price_toman=Decimal("30000"), price_rial=Decimal("300000"), is_available=True, is_popular=False, is_new=True)
        item4 = MenuItem(id=4, category_id=test_category.id, name="Unavailable Item", price_toman=Decimal("40000"), price_rial=Decimal("400000"), is_available=False)
        db.add_all([item1, item2, item3, item4])
        await db.commit()
        
        # Filter by available
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items?is_available=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3  # Only available items
        
        # Filter by popular
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items?is_popular=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Popular Item"
        
        # Search
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items?search=Popular",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

    async def test_get_menu_item(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, test_category: Category, db: AsyncSession):
        item = MenuItem(id=1, category_id=test_category.id, name="Test Item", price_toman=Decimal("15000"), price_rial=Decimal("150000"))
        db.add(item)
        await db.commit()
        await db.refresh(item)
        
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items/{item.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item.id
        assert data["name"] == "Test Item"

    async def test_update_menu_item(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, test_category: Category, db: AsyncSession):
        item = MenuItem(id=1, category_id=test_category.id, name="Original", price_toman=Decimal("10000"), price_rial=Decimal("100000"))
        db.add(item)
        await db.commit()
        await db.refresh(item)
        
        response = await client.put(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items/{item.id}",
            json={
                "name": "Updated Name",
                "price_toman": "20000",
                "price_rial": "200000",
                "is_available": False
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["price_toman"] == "20000.00"
        assert data["is_available"] is False

    async def test_delete_menu_item(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, test_category: Category, db: AsyncSession):
        item = MenuItem(id=1, category_id=test_category.id, name="To Delete", price_toman=Decimal("10000"), price_rial=Decimal("100000"))
        db.add(item)
        await db.commit()
        await db.refresh(item)
        
        response = await client.delete(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items/{item.id}",
            headers=auth_headers
        )
        assert response.status_code == 204
        
        await db.refresh(item)
        assert item.is_available is False  # Soft delete


class TestMenuItemOptions:
    async def test_create_option(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, test_category: Category, db: AsyncSession):
        item = MenuItem(id=1, category_id=test_category.id, name="Burger", price_toman=Decimal("50000"), price_rial=Decimal("500000"))
        db.add(item)
        await db.commit()
        await db.refresh(item)
        
        response = await client.post(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items/{item.id}/options",
            json={
                "name": "Extra Cheese",
                "price_adjustment_toman": "5000",
                "price_adjustment_rial": "50000",
                "is_required": False,
                "display_order": 1
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Extra Cheese"
        assert data["price_adjustment_toman"] == "5000.00"
        assert data["is_required"] is False

    async def test_list_options(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, test_category: Category, db: AsyncSession):
        item = MenuItem(id=1, category_id=test_category.id, name="Pizza", price_toman=Decimal("80000"), price_rial=Decimal("800000"))
        db.add(item)
        await db.commit()
        await db.refresh(item)
        
        option1 = MenuItemOption(id=1, menu_item_id=item.id, name="Option 1", price_adjustment_toman=Decimal("5000"), price_adjustment_rial=Decimal("50000"), display_order=1)
        option2 = MenuItemOption(id=2, menu_item_id=item.id, name="Option 2", price_adjustment_toman=Decimal("10000"), price_adjustment_rial=Decimal("100000"), display_order=2)
        db.add_all([option1, option2])
        await db.commit()
        
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items/{item.id}/options",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["display_order"] == 1  # Ordered by display_order

    async def test_update_option(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, test_category: Category, db: AsyncSession):
        item = MenuItem(id=1, category_id=test_category.id, name="Item", price_toman=Decimal("10000"), price_rial=Decimal("100000"))
        db.add(item)
        await db.commit()
        await db.refresh(item)
        
        option = MenuItemOption(id=1, menu_item_id=item.id, name="Original", price_adjustment_toman=Decimal("1000"), price_adjustment_rial=Decimal("10000"))
        db.add(option)
        await db.commit()
        await db.refresh(option)
        
        response = await client.put(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items/{item.id}/options/{option.id}",
            json={
                "name": "Updated Option",
                "price_adjustment_toman": "2000"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Option"
        assert data["price_adjustment_toman"] == "2000.00"

    async def test_delete_option(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, test_category: Category, db: AsyncSession):
        item = MenuItem(id=1, category_id=test_category.id, name="Item", price_toman=Decimal("10000"), price_rial=Decimal("100000"))
        db.add(item)
        await db.commit()
        await db.refresh(item)
        
        option = MenuItemOption(id=1, menu_item_id=item.id, name="To Delete", price_adjustment_toman=Decimal("1000"), price_adjustment_rial=Decimal("10000"))
        db.add(option)
        await db.commit()
        await db.refresh(option)
        
        response = await client.delete(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{test_category.id}/items/{item.id}/options/{option.id}",
            headers=auth_headers
        )
        assert response.status_code == 204
        
        # Verify deleted
        result = await db.execute(
            select(MenuItemOption).where(MenuItemOption.id == option.id)
        )
        assert result.scalar_one_or_none() is None