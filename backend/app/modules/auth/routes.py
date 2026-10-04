from fastapi import APIRouter, Depends, status
from app.modules.auth.schemas import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    UserCreate,
    UserUpdate,
)
from app.modules.auth.service import AuthService
from app.modules.auth.dependencies import get_auth_service, get_current_user, require_superuser
from app.core.models import User


router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="User login")
async def login(
    credentials: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    user = await auth_service.authenticate(credentials.email, credentials.password)
    if not user:
        from app.core.exceptions import UnauthorizedException
        raise UnauthorizedException("Invalid email or password")
    return await auth_service.create_tokens(user)


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.refresh_tokens(request.refresh_token)


@router.get("/me", response_model=UserResponse, summary="Get current user")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create user (superuser only)")
async def create_user(
    data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
    _: User = Depends(require_superuser),
):
    return await auth_service.create_user(data)


@router.get("/users/{user_id}", response_model=UserResponse, summary="Get user by ID (superuser only)")
async def get_user(
    user_id: int,
    auth_service: AuthService = Depends(get_auth_service),
    _: User = Depends(require_superuser),
):
    return await auth_service.get_user(user_id)


@router.put("/users/{user_id}", response_model=UserResponse, summary="Update user (superuser only)")
async def update_user(
    user_id: int,
    data: UserUpdate,
    auth_service: AuthService = Depends(get_auth_service),
    _: User = Depends(require_superuser),
):
    return await auth_service.update_user(user_id, data)