from app.modules.auth.routes import router
from app.modules.auth.service import AuthService
from app.modules.auth.dependencies import (
    get_auth_service,
    get_current_user,
    get_optional_user,
    require_role,
    require_superuser,
    require_owner_or_admin,
)
from app.modules.auth.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    UserCreate,
    UserUpdate,
)

__all__ = [
    "router",
    "AuthService",
    "get_auth_service",
    "get_current_user",
    "get_optional_user",
    "require_role",
    "require_superuser",
    "require_owner_or_admin",
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "UserResponse",
    "UserCreate",
    "UserUpdate",
]