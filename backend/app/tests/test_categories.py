import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import User, Restaurant, Branch, Menu, Category, MenuItem
from app.core.security import create_access_token


class TestCategories:
    async def test_create_category(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu):
        response = await client.post(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories",
            json={
                "name": "Appetizers",
                "slug": "appetizers",
                "display_order": 1,
                "is_visible": True,
                "translation": {}
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Appetizers"
        assert data["menu_id"] == test_menu.id
        assert data["parent_id"] is None

    async def test_create_subcategory(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, db: AsyncSession):
        parent = Category(id=1, menu_id=test_menu.id, name="Main", slug="main", display_order=1)
        db.add(parent)
        await db.commit()
        await db.refresh(parent)
        
        response = await client.post(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories",
            json={
                "name": "Sub Item",
                "slug": "sub-item",
                "parent_id": parent.id,
                "display_order": 1,
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["parent_id"] == parent.id

    async def test_create_category_invalid_parent(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu):
        response = await client.post(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories",
            json={
                "name": "Invalid",
                "slug": "invalid",
                "parent_id": 99999,
            },
            headers=auth_headers
        )
        assert response.status_code == 404

    async def test_list_categories(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, db: AsyncSession):
        for i in range(3):
            cat = Category(id=i+1, menu_id=test_menu.id, name=f"Category {i}", slug=f"cat-{i}", display_order=i)
            db.add(cat)
        await db.commit()
        
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    async def test_list_categories_filter_parent(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, db: AsyncSession):
        parent = Category(id=1, menu_id=test_menu.id, name="Parent", slug="parent", display_order=1)
        db.add(parent)
        await db.commit()
        await db.refresh(parent)
        
        child = Category(id=2, menu_id=test_menu.id, name="Child", slug="child", parent_id=parent.id, display_order=1)
        db.add(child)
        await db.commit()
        
        # Get root categories
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories?parent_id=0",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == parent.id
        
        # Get children
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories?parent_id={parent.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == child.id

    async def test_get_category_tree(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, db: AsyncSession):
        parent = Category(id=1, menu_id=test_menu.id, name="Parent", slug="parent", display_order=1, is_visible=True)
        db.add(parent)
        await db.commit()
        await db.refresh(parent)
        
        child1 = Category(id=2, menu_id=test_menu.id, name="Child 1", slug="child1", parent_id=parent.id, display_order=1, is_visible=True)
        child2 = Category(id=3, menu_id=test_menu.id, name="Child 2", slug="child2", parent_id=parent.id, display_order=2, is_visible=True)
        db.add_all([child1, child2])
        await db.commit()
        
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/tree",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == parent.id
        assert len(data[0]["children"]) == 2

    async def test_get_category(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, db: AsyncSession):
        category = Category(id=1, menu_id=test_menu.id, name="Test Category", slug="test-category", display_order=1)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        response = await client.get(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{category.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category.id

    async def test_update_category(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, db: AsyncSession):
        category = Category(id=1, menu_id=test_menu.id, name="Original", slug="original", display_order=1)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        response = await client.put(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{category.id}",
            json={
                "name": "Updated",
                "display_order": 5
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["display_order"] == 5

    async def test_update_category_cannot_be_own_parent(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, db: AsyncSession):
        category = Category(id=1, menu_id=test_menu.id, name="Category", slug="category", display_order=1)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        response = await client.put(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{category.id}",
            json={"parent_id": category.id},
            headers=auth_headers
        )
        assert response.status_code == 422

    async def test_delete_category(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, db: AsyncSession):
        category = Category(id=1, menu_id=test_menu.id, name="To Delete", slug="to-delete", display_order=1)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        response = await client.delete(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{category.id}",
            headers=auth_headers
        )
        assert response.status_code == 204

    async def test_delete_category_with_children_fails(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, db: AsyncSession):
        parent = Category(id=1, menu_id=test_menu.id, name="Parent", slug="parent", display_order=1)
        db.add(parent)
        await db.commit()
        await db.refresh(parent)
        
        child = Category(id=2, menu_id=test_menu.id, name="Child", slug="child", parent_id=parent.id, display_order=1)
        db.add(child)
        await db.commit()
        
        response = await client.delete(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{parent.id}",
            headers=auth_headers
        )
        assert response.status_code == 409

    async def test_delete_category_with_items_fails(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, test_menu: Menu, db: AsyncSession):
        category = Category(id=1, menu_id=test_menu.id, name="Category", slug="category", display_order=1)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        item = MenuItem(id=1, category_id=category.id, name="Item", price_toman=10000, price_rial=100000)
        db.add(item)
        await db.commit()
        
        response = await client.delete(
            f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{test_menu.id}/categories/{category.id}",
            headers=auth_headers
        )
        assert response.status_code == 409