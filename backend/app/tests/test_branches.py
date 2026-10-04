import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import User, Restaurant, Branch
from app.core.security import create_access_token


class TestBranches:
    async def test_create_branch(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant):
        response = await client.post(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches", json={
            "name": "Main Branch",
            "code": "MAIN",
            "address": "123 Main St",
            "phone": "+982112345678",
            "latitude": 35.6892,
            "longitude": 51.3890,
            "settings": {},
            "operating_hours": {}
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Main Branch"
        assert data["code"] == "MAIN"
        assert data["restaurant_id"] == test_restaurant.id
        assert data["is_active"] is True

    async def test_create_branch_duplicate_code(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, db: AsyncSession):
        branch = Branch(id=1, restaurant_id=test_restaurant.id, name="Existing", code="EXIST")
        db.add(branch)
        await db.commit()
        
        response = await client.post(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches", json={
            "name": "New Branch",
            "code": "EXIST",
        }, headers=auth_headers)
        assert response.status_code == 409

    async def test_list_branches(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, db: AsyncSession):
        for i in range(3):
            branch = Branch(id=i+1, restaurant_id=test_restaurant.id, name=f"Branch {i}", code=f"B{i}")
            db.add(branch)
        await db.commit()
        
        response = await client.get(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_get_branch(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, db: AsyncSession):
        branch = Branch(id=1, restaurant_id=test_restaurant.id, name="Test Branch", code="TEST")
        db.add(branch)
        await db.commit()
        await db.refresh(branch)
        
        response = await client.get(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{branch.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == branch.id
        assert data["name"] == "Test Branch"

    async def test_get_branch_not_found(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant):
        response = await client.get(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/99999", headers=auth_headers)
        assert response.status_code == 404

    async def test_update_branch(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, db: AsyncSession):
        branch = Branch(id=1, restaurant_id=test_restaurant.id, name="Original", code="ORIG")
        db.add(branch)
        await db.commit()
        await db.refresh(branch)
        
        response = await client.put(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{branch.id}", json={
            "name": "Updated Name",
            "address": "New Address"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["address"] == "New Address"
        assert data["code"] == "ORIG"

    async def test_update_branch_code_conflict(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, db: AsyncSession):
        branch1 = Branch(id=1, restaurant_id=test_restaurant.id, name="Branch 1", code="B1")
        branch2 = Branch(id=2, restaurant_id=test_restaurant.id, name="Branch 2", code="B2")
        db.add_all([branch1, branch2])
        await db.commit()
        
        response = await client.put(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{branch2.id}", json={
            "code": "B1"
        }, headers=auth_headers)
        assert response.status_code == 409

    async def test_delete_branch(self, client: AsyncClient, auth_headers: dict, test_restaurant: Restaurant, db: AsyncSession):
        branch = Branch(id=1, restaurant_id=test_restaurant.id, name="To Delete", code="DEL")
        db.add(branch)
        await db.commit()
        await db.refresh(branch)
        
        response = await client.delete(f"/api/v1/admin/restaurants/{test_restaurant.id}/branches/{branch.id}", headers=auth_headers)
        assert response.status_code == 204
        
        await db.refresh(branch)
        assert branch.is_active is False

    async def test_branch_restaurant_isolation(self, client: AsyncClient, db: AsyncSession):
        # Create two users with restaurants
        user1 = User(id=10, email="user1@example.com", password_hash="hashed", role="owner")
        user2 = User(id=11, email="user2@example.com", password_hash="hashed", role="owner")
        db.add_all([user1, user2])
        await db.commit()
        
        restaurant1 = Restaurant(id=1, name="User1 Restaurant", slug="user1-restaurant", owner_id=user1.id)
        restaurant2 = Restaurant(id=2, name="User2 Restaurant", slug="user2-restaurant", owner_id=user2.id)
        db.add_all([restaurant1, restaurant2])
        await db.commit()
        
        # Create branch for user1
        branch = Branch(id=1, restaurant_id=restaurant1.id, name="User1 Branch", code="U1B1")
        db.add(branch)
        await db.commit()
        await db.refresh(branch)
        
        # Create token for user2
        token = create_access_token(data={"sub": str(user2.id), "email": user2.email, "role": user2.role})
        user2_headers = {"Authorization": f"Bearer {token}"}
        
        # user2 should not access user1's branches
        response = await client.get(f"/api/v1/admin/restaurants/{restaurant1.id}/branches", headers=user2_headers)
        assert response.status_code == 403
        
        response = await client.get(f"/api/v1/admin/restaurants/{restaurant1.id}/branches/{branch.id}", headers=user2_headers)
        assert response.status_code == 403