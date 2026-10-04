from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from fastapi.exceptions import RequestValidationError

from app.core import (
    get_settings,
    init_db,
    close_db,
    RequestIDMiddleware,
    TenantContextMiddleware,
    RateLimitMiddleware,
    app_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    generic_exception_handler,
    AppException,
)
from app.modules.auth.routes import router as auth_router
from app.modules.restaurants.routes import router as restaurants_router
from app.modules.branches.routes import router as branches_router
from app.modules.menus.routes import router as menus_router
from app.modules.categories.routes import router as categories_router
from app.modules.menu_items.routes import router as menu_items_router
from app.modules.public.routes import router as public_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
    )

    # Middleware (applied in reverse order - last added executes first)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TenantContextMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Health endpoints
    @app.get("/health/live", tags=["health"])
    async def liveness():
        return {"status": "alive"}

    @app.get("/health/ready", tags=["health"])
    async def readiness():
        return {"status": "ready"}

    # API routes
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(restaurants_router, prefix="/api/v1/admin", tags=["restaurants"])
    app.include_router(branches_router, prefix="/api/v1/admin", tags=["branches"])
    app.include_router(menus_router, prefix="/api/v1/admin", tags=["menus"])
    app.include_router(categories_router, prefix="/api/v1/admin", tags=["categories"])
    app.include_router(menu_items_router, prefix="/api/v1/admin", tags=["menu-items"])
    app.include_router(public_router, prefix="/api/v1/public", tags=["public"])

    return app


app = create_app()