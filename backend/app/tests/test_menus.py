import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import User, Restaurant, Branch, Menu
from app.core.security import create_access_token


class TestMenus:
    async def test_create_menu(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch):
        response = await client.post(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus", json={
            "name": "Lunch Menu",
            "description": "Lunch specials",
            "is_active": True,
            "is_default": True,
            "branding": {}
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Lunch Menu"
        assert data["branch_id"] == test_branch.id
        assert data["is_default"] is True

    async def test_create_menu_default_unsets_others(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, db: AsyncSession):
        # Create first default menu
        menu1 = Menu(id=1, branch_id=test_branch.id, name="Menu 1", is_default=True, is_active=True)
        db.add(menu1)
        await db.commit()
        
        # Create second default menu - should unset first
        response = await client.post(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus", json={
            "name": "Menu 2",
            "is_default": True,
        }, headers=auth_headers)
        assert response.status_code == 201
        
        await db.refresh(menu1)
        assert menu1.is_default is False

    async def test_list_menus(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, db: AsyncSession):
        for i in range(3):
            menu = Menu(id=i+1, branch_id=test_branch.id, name=f"Menu {i}", is_active=True)
            db.add(menu)
        await db.commit()
        
        response = await client.get(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    async def test_get_menu(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, db: AsyncSession):
        menu = Menu(id=1, branch_id=test_branch.id, name="Test Menu", is_active=True)
        db.add(menu)
        await db.commit()
        await db.refresh(menu)
        
        response = await client.get(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{menu.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == menu.id
        assert data["name"] == "Test Menu"

    async def test_update_menu(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, db: AsyncSession):
        menu = Menu(id=1, branch_id=test_branch.id, name="Original", is_active=True)
        db.add(menu)
        await db.commit()
        await db.refresh(menu)
        
        response = await client.put(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{menu.id}", json={
            "name": "Updated Menu",
            "description": "New description"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Menu"
        assert data["description"] == "New description"

    async def test_update_menu_set_default(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, db: AsyncSession):
        menu1 = Menu(id=1, branch_id=test_branch.id, name="Menu 1", is_default=True, is_active=True)
        menu2 = Menu(id=2, branch_id=test_branch.id, name="Menu 2", is_active=True)
        db.add_all([menu1, menu2])
        await db.commit()
        
        response = await client.put(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{menu2.id}", json={
            "is_default": True
        }, headers=auth_headers)
        assert response.status_code == 200
        
        await db.refresh(menu1)
        await db.refresh(menu2)
        assert menu1.is_default is False
        assert menu2.is_default is True

    async def test_delete_menu(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, test_branch: Branch, db: AsyncSession):
        menu = Menu(id=1, branch_id=test_branch.id, name="To Delete", is_active=True)
        db.add(menu)
        await db.commit()
        await db.refresh(menu)
        
        response = await client.delete(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{test_branch.id}/menus/{menu.id}", headers=auth_headers)
        assert response.status_code == 204
        
        await db.refresh(menu)
        assert menu.is_active is False

    async def test_menu_isolation(self, client: AsyncClient, db: AsyncSession):
        user1 = User(id=10, email="user1@example.com", password_hash="hashed", role="owner")
        user2 = User(id=11, email="user2@example.com", password_hash="hashed", role="owner")
        db.add_all([user1, user2])
        await db.commit()
        
        restaurant1 = Restaurant(id=1, name="User1 Restaurant", slug="user1-restaurant", owner_id=user1.id)
        restaurant2 = Restaurant(id=2, name="User2 Restaurant", slug="user2-restaurant", owner_id=user2.id)
        db.add_all([restaurant1, restaurant2])
        await db.commit()
        
        branch1 = Branch(id=1, restaurant_id=restaurant1.id, name="Branch 1", code="B1")
        branch2 = Branch(id=2, restaurant_id=restaurant2.id, name="Branch 2", code="B2")
        db.add_all([branch1, branch2])
        await db.commit()
        
        menu = Menu(id=1, branch_id=branch1.id, name="User1 Menu", is_active=True)
        db.add(menu)
        await db.commit()
        await db.refresh(menu)
        
        # Create token for user2
        token = create_access_token(data={"sub": str(user2.id), "email": user2.email, "role": user2.role})
        user2_headers = {"Authorization": f"Bearer {token}"}
        
        # user2 should not access user1's menus
        response = await client.get(f"/api/v1/admin/restaurants/{restaurant1.id}/branches/{branch1.id}/menus", headers=user2_headers)
        assert response.status_code == 403