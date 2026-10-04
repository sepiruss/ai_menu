from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import get_db, decode_token, verify_token_type
from app.core.exceptions import UnauthorizedException
from app.core.models import User
from app.modules.auth.service import AuthService


security = HTTPBearer(auto_error=False)


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    if not credentials:
        raise UnauthorizedException("Authentication required")
    
    return await auth_service.get_current_user(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> User | None:
    if not credentials:
        return None
    try:
        return await auth_service.get_current_user(credentials.credentials)
    except UnauthorizedException:
        return None


def require_role(*allowed_roles: str):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            from app.core.exceptions import ForbiddenException
            raise ForbiddenException(f"Required role: {', '.join(allowed_roles)}")
        return current_user
    return role_checker


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Superuser access required")
    return current_user


def require_owner_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("owner", "admin", "manager", "superuser"):
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException("Owner, admin, manager, or superuser access required")
    return current_user