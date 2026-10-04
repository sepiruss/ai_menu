from datetime import timedelta, datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    hash_refresh_token,
)
from app.core.exceptions import UnauthorizedException, NotFoundException
from app.core.models import User, RefreshToken
from app.modules.auth.schemas import LoginRequest, TokenResponse, UserCreate, UserUpdate


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate(self, email: str, password: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    async def create_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        raw_refresh_token, token_hash, expires_at = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        # Store refresh token hash in database
        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(refresh_token)
        await self.db.commit()
        
        return TokenResponse(access_token=access_token, refresh_token=raw_refresh_token)

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        token_hash = hash_refresh_token(refresh_token)
        
        # Find the refresh token in database
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_token = result.scalar_one_or_none()
        
        if not stored_token:
            raise UnauthorizedException("Invalid refresh token")
        
        if stored_token.revoked_at is not None:
            # Token already used - potential token reuse attack, revoke all user tokens
            await self.revoke_all_user_tokens(stored_token.user_id)
            raise UnauthorizedException("Refresh token already used")
        
        if stored_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise UnauthorizedException("Refresh token expired")
        
        # Revoke the current token (rotation)
        stored_token.revoked_at = datetime.now(timezone.utc)
        
        # Get user and create new tokens
        user = await self.db.get(User, stored_token.user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive")
        
        return await self.create_tokens(user)

    async def revoke_all_user_tokens(self, user_id: int) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None)
            )
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def get_current_user(self, token: str) -> User:
        payload = decode_token(token)
        if not payload or not verify_token_type(payload, "access"):
            raise UnauthorizedException("Invalid access token")
        
        user_id = int(payload.get("sub", 0))
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or inactive")
        
        return user

    async def create_user(self, data: UserCreate) -> User:
        # Check if email exists
        result = await self.db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            from app.core.exceptions import ConflictException
            raise ConflictException("user", "Email already registered")
        
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_user(self, user_id: int) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User", user_id)
        return user

    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        user = await self.get_user(user_id)
        
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.role is not None:
            user.role = data.role
        if data.is_active is not None:
            user.is_active = data.is_active
        
        await self.db.commit()
        await self.db.refresh(user)
        return user