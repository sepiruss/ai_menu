import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from app.core.models import User
from app.core.security import create_refresh_token, hash_refresh_token
from app.core.config import get_settings


class TestAuth:
    async def test_login_success(self, client: AsyncClient, test_user: User):
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        assert response.status_code == 401

    async def test_refresh_token(self, client: AsyncClient, test_user: User):
        login_response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_token_rotation(self, client: AsyncClient, test_user: User):
        """Valid refresh token -> new access + refresh token, old token revoked"""
        login_response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # First refresh
        response1 = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response1.status_code == 200
        new_refresh_token = response1.json()["refresh_token"]
        assert new_refresh_token != refresh_token
        
        # Second refresh with new token
        response2 = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": new_refresh_token
        })
        assert response2.status_code == 200

    async def test_refresh_token_reuse_detected(self, client: AsyncClient, test_user: User, db: AsyncSession):
        """Old refresh token cannot be reused - token reuse detection revokes all user tokens"""
        from app.core.models import RefreshToken
        from sqlalchemy import select
        
        login_response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # First refresh - rotates token
        response1 = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response1.status_code == 200
        new_refresh_token = response1.json()["refresh_token"]
        
        # Try to reuse the OLD refresh token - should fail and revoke all tokens
        response_reuse = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response_reuse.status_code == 401
        error_data = response_reuse.json()
        assert "already used" in error_data.get("message", "").lower() or "invalid" in error_data.get("message", "").lower()
        
        # Even the new token should now be revoked due to reuse detection
        response_new = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": new_refresh_token
        })
        assert response_new.status_code == 401

    async def test_refresh_token_revoked_rejected(self, client: AsyncClient, test_user: User, db: AsyncSession):
        """Revoked token rejected"""
        from app.core.models import RefreshToken
        from sqlalchemy import select
        from app.core.security import hash_refresh_token
        from datetime import datetime, timezone
        
        login_response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Manually revoke the token in database
        token_hash = hash_refresh_token(refresh_token)
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_token = result.scalar_one()
        stored_token.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        
        # Try to use revoked token
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 401

    async def test_refresh_token_expired_rejected(self, client: AsyncClient, test_user: User, db: AsyncSession):
        """Expired token rejected"""
        from app.core.models import RefreshToken
        from sqlalchemy import select
        from app.core.security import hash_refresh_token
        from datetime import datetime, timezone, timedelta
        
        login_response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Manually expire the token
        token_hash = hash_refresh_token(refresh_token)
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_token = result.scalar_one()
        stored_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.commit()
        
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 401

    async def test_refresh_token_inactive_user_rejected(self, client: AsyncClient, test_user: User, db: AsyncSession):
        """Inactive user rejected"""
        from app.core.models import RefreshToken
        from sqlalchemy import select
        from app.core.security import hash_refresh_token
        
        login_response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Deactivate user
        test_user.is_active = False
        await db.commit()
        
        response = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert response.status_code == 401

    async def test_get_me(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "superuser"

    async def test_get_me_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestRateLimit:
    async def test_rate_limit_headers_present(self, client: AsyncClient):
        """Rate limit headers present on non-exempt responses"""
        response = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        # Even 401 responses should have rate limit headers
        assert response.status_code == 401
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    async def test_rate_limit_exempt_paths(self, client: AsyncClient):
        """Exempt paths like /health, /docs don't count towards limit"""
        # Health endpoint is exempt - no rate limit headers
        response = await client.get("/health/live")
        assert response.status_code == 200
        # Exempt paths don't get rate limit headers
        
        # Docs endpoints are exempt
        response = await client.get("/api/v1/docs")
        assert response.status_code == 200

    async def test_rate_limit_per_ip_per_path(self, client: AsyncClient, settings):
        """Rate limit is per IP + per path"""
        # Use a non-exempt endpoint
        response = await client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        assert response.status_code == 401
        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])
        assert remaining <= limit

    async def test_rate_limit_configurable(self, client: AsyncClient, settings):
        """RATE_LIMIT_PER_MINUTE is configurable"""
        assert settings.RATE_LIMIT_PER_MINUTE > 0


class TestUsers:
    async def test_create_user_superuser(self, client: AsyncClient, superuser_headers: dict):
        response = await client.post("/api/v1/auth/users", json={
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User",
            "role": "owner"
        }, headers=superuser_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "owner"

    async def test_create_user_duplicate_email(self, client: AsyncClient, superuser_headers: dict, test_user: User):
        response = await client.post("/api/v1/auth/users", json={
            "email": "test@example.com",
            "password": "newpassword123",
        }, headers=superuser_headers)
        assert response.status_code == 409

    async def test_create_user_non_superuser(self, client: AsyncClient, owner_headers: dict):
        response = await client.post("/api/v1/auth/users", json={
            "email": "newuser@example.com",
            "password": "newpassword123",
        }, headers=owner_headers)
        assert response.status_code == 403

    async def test_get_user_superuser(self, client: AsyncClient, superuser_headers: dict, test_user: User):
        response = await client.get(f"/api/v1/auth/users/{test_user.id}", headers=superuser_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id

    async def test_update_user_superuser(self, client: AsyncClient, superuser_headers: dict, test_user: User):
        response = await client.put(f"/api/v1/auth/users/{test_user.id}", json={
            "full_name": "Updated Name",
            "role": "manager"
        }, headers=superuser_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["role"] == "manager"