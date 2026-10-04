import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import User, Restaurant
from app.core.security import create_access_token


class TestRestaurants:
    async def test_create_restaurant(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/api/v1/admin/restaurants", json={
            "name": "Test Restaurant",
            "slug": "test-restaurant-new",
            "description": "A test restaurant",
            "timezone": "Asia/Tehran",
            "settings": {},
            "branding": {}
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Restaurant"
        assert data["slug"] == "test-restaurant-new"
        assert data["is_active"] is True

    async def test_create_restaurant_duplicate_slug(self, client: AsyncClient, auth_headers: dict, db: AsyncSession, test_user: User):
        # Create first restaurant
        restaurant = Restaurant(
            id=10,
            name="First Restaurant",
            slug="first-restaurant",
            owner_id=test_user.id,
        )
        db.add(restaurant)
        await db.commit()
        
        # Try to create with same slug
        response = await client.post("/api/v1/admin/restaurants", json={
            "name": "Second Restaurant",
            "slug": "first-restaurant",
        }, headers=auth_headers)
        assert response.status_code == 409

    async def test_list_restaurants(self, client: AsyncClient, auth_headers: dict, db: AsyncSession, test_user: User):
        # Create a few restaurants
        for i in range(3):
            restaurant = Restaurant(
                id=20+i,
                name=f"Restaurant {i}",
                slug=f"restaurant-{i}",
                owner_id=test_user.id,
            )
            db.add(restaurant)
        await db.commit()
        
        response = await client.get("/api/v1/admin/restaurants", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_restaurants_pagination(self, client: AsyncClient, auth_headers: dict, db: AsyncSession, test_user: User):
        for i in range(5):
            restaurant = Restaurant(
                id=30+i,
                name=f"Restaurant {i}",
                slug=f"restaurant-{i}-p",
                owner_id=test_user.id,
            )
            db.add(restaurant)
        await db.commit()
        
        response = await client.get("/api/v1/admin/restaurants?page=1&page_size=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_get_restaurant(self, client: AsyncClient, auth_headers: dict, db: AsyncSession, test_user: User):
        restaurant = Restaurant(
            id=40,
            name="Test Restaurant",
            slug="test-restaurant-get",
            owner_id=test_user.id,
        )
        db.add(restaurant)
        await db.commit()
        await db.refresh(restaurant)
        
        response = await client.get(f"/api/v1/admin/restaurants/{restaurant.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == restaurant.id
        assert data["name"] == "Test Restaurant"

    async def test_get_restaurant_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/admin/restaurants/99999", headers=auth_headers)
        assert response.status_code == 404

    async def test_update_restaurant(self, client: AsyncClient, auth_headers: dict, db: AsyncSession, test_user: User):
        restaurant = Restaurant(
            id=50,
            name="Original Name",
            slug="original-slug",
            owner_id=test_user.id,
        )
        db.add(restaurant)
        await db.commit()
        await db.refresh(restaurant)
        
        response = await client.put(f"/api/v1/admin/restaurants/{restaurant.id}", json={
            "name": "Updated Name",
            "description": "Updated description"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"
        assert data["slug"] == "original-slug"  # unchanged

    async def test_update_restaurant_slug_conflict(self, client: AsyncClient, auth_headers: dict, db: AsyncSession, test_user: User):
        restaurant1 = Restaurant(id=60, name="Restaurant 1", slug="restaurant-1", owner_id=test_user.id)
        restaurant2 = Restaurant(id=61, name="Restaurant 2", slug="restaurant-2", owner_id=test_user.id)
        db.add_all([restaurant1, restaurant2])
        await db.commit()
        
        response = await client.put(f"/api/v1/admin/restaurants/{restaurant2.id}", json={
            "slug": "restaurant-1"
        }, headers=auth_headers)
        assert response.status_code == 409

    async def test_delete_restaurant(self, client: AsyncClient, auth_headers: dict, db: AsyncSession, test_user: User):
        restaurant = Restaurant(
            id=70,
            name="To Delete",
            slug="to-delete",
            owner_id=test_user.id,
        )
        db.add(restaurant)
        await db.commit()
        await db.refresh(restaurant)
        
        response = await client.delete(f"/api/v1/admin/restaurants/{restaurant.id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify soft delete
        await db.refresh(restaurant)
        assert restaurant.is_active is False

    async def test_restaurant_isolation(self, client: AsyncClient, db: AsyncSession):
        # Create two users with explicit IDs
        user1 = User(id=100, email="user1@example.com", password_hash="hashed", role="owner")
        user2 = User(id=101, email="user2@example.com", password_hash="hashed", role="owner")
        db.add_all([user1, user2])
        await db.commit()
        
        # Create restaurant for user1 with a unique ID
        restaurant = Restaurant(id=200, name="User1 Restaurant", slug="user1-restaurant", owner_id=user1.id)
        db.add(restaurant)
        await db.commit()
        await db.refresh(restaurant)
        
        # Create token for user2
        token = create_access_token(data={"sub": str(user2.id), "email": user2.email, "role": user2.role})
        user2_headers = {"Authorization": f"Bearer {token}"}
        
        # user2 should not see user1's restaurant
        response = await client.get("/api/v1/admin/restaurants", headers=user2_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        
        # user2 should not access user1's restaurant (returns 404 because user2 doesn't own it)
        response = await client.get(f"/api/v1/admin/restaurants/{restaurant.id}", headers=user2_headers)
        assert response.status_code == 404  # Not found because user2 doesn't own it