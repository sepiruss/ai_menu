# Smart Digital Menu - Backend Structure

## Overall Package Structure
```
sepehr-backend/
  app/
    __init__.py        # FastAPI app factory
    config.py          # Configuration/settings
    constants.py       # Constants (event types, roles, etc.)
    middleware.py      # Request middleware (auth, tenant, logging)
    exceptions.py      # Custom exceptions
    
    /api/
      /v1/
        /auth/
          routes.py      # Login, refresh, logout
          schemas.py     # Auth Pydantic schemas
        /public/
          /menu/
            routes.py    # Menu browsing APIs
            schemas.py   # Public menu schemas
          /sessions/
            routes.py    # Customer session management
            schemas.py   # Session schemas
          /events/
            routes.py    # Event tracking
            schemas.py   # Event schemas
          /recommendations/
            routes.py    # Recommendation APIs
            schemas.py   # Recommendation schemas
        /admin/
          /restaurants/
            routes.py      # Restaurant CRUD
            schemas.py     # Restaurant schemas
          /branches/
            routes.py      # Branch CRUD
            schemas.py     # Branch schemas
          /menus/
            routes.py      # Menu management
            schemas.py     # Menu schemas
          /categories/
            routes.py      # Category management
            schemas.py     # Category schemas
          /menu-items/
            routes.py      # Item CRUD with options
            schemas.py     # Item schemas
          /tables/
            routes.py      # Table management
            schemas.py     # Table schemas
          /orders/
            routes.py      # Order lifecycle
            schemas.py     # Order schemas
          /payments/
            routes.py      # Payment processing
            schemas.py     # Payment schemas
          /customers/
            routes.py      # Customer management
            schemas.py     # Customer schemas
          /events/
            routes.py      # Event analytics
            schemas.py     # Event schemas
          /recommendations/
            routes.py      # Recommendation management
            schemas.py     # Recommendation schemas
          /subscriptions/
            routes.py      # Billing/subscriptions
            schemas.py     # Subscription schemas
          /analytics/
            routes.py      # Analytics endpoints
            schemas.py     # Analytics schemas
          
    /modules/          # Module-based organization
      /auth/
        models.py        # User, refresh token
        services.py      # Auth logic (JWT, password)
        dependencies.py  # FastAPI dependencies
      /restaurants/
        models.py        # Restaurant model
        services.py      # Restaurant business logic
        routers.py       # Router registration
      /branches/
        models.py        # Branch model
        services.py      # Branch business logic
      /staff/
        models.py        # Staff members, roles
        services.py      # Staff management
      /menus/
        models.py        # Menu, menu items
        services.py      # Menu business logic
        dependencies.py  # Menu access checks
      /categories/
        models.py        # Categories with self-ref
        services.py      # Category operations
      /menu-items/
        models.py        # Items, options, allergens
        services.py      # Item management with options
      /tables/
        models.py        # Table model
        services.py      # Table operations
      /qr_codes/
        models.py        # QR code model
        services.py      # QR generation
      /customers/
        models.py        # Customer, sessions
        services.py      # Customer lifecycle
      /orders/
        models.py        # Orders, items
        services.py      # Order processing
      /payments/
        models.py        # Payments, transactions
        services.py      # Payment provider abstraction
      /analytics/
        services.py      # Analytics calculation
      /events/
        services.py      # Event pipeline, processing
      /recommendations/
        engine.py        # RecommendationEngine abstraction
        implementations/
          /popular.py    # PopularItemsRecommendation
          /content_based.py # ContentBasedRecommendation
          /collaborative.py # CollaborativeFilteringRecommendation
        schemas.py
      /subscriptions/
        models.py        # Subscription model
        services.py      # Billing logic
        
    /shared/
      /db/
        database.py      # SQLAlchemy engine, session
        migrations.py    # Alembic setup
        base.py          # Base model mixins (tenant_id, timestamps)
      /security/
        auth.py          # Password, JWT utilities
        permissions.py   # RBAC checks
      /utils/
        helpers.py       # General utilities
        validators.py    # Input validators
      /logging/
        config.py        # Structured logging
        ids.py          # Request ID generation
      
    /tests/
      /unit/
        /modules/        # Unit tests per module
      /integration/
        /api/           # API integration tests
        /database/      # DB tests
      /fixtures/        # Test data
      
  requirements.txt   # Python dependencies
  .env.example       # Environment variables example
  docker-compose.yml # Local development
  Dockerfile         # Production Docker
```

## Module Organization Details

### 1. auth Module
**Purpose:** Authentication and authorization for the entire system.

**Key Components:**
- `models.py`: User model, API keys, refresh tokens
- `services.py`: 
  - Login with password verification
  - JWT token creation and validation
  - Refresh token rotation
  - Password hashing (bcrypt)
- `routes.py`:
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/refresh`
  - `POST /api/v1/auth/logout`
- `dependencies.py`:
  - `get_current_user` - JWT dependency
  - `get_current_restaurant` - Tenant resolver
  - `require_roles` - Role-based access

**Design Decisions:**
- Passwords never stored as plain text (bcrypt Argon2)
- JWT includes `restaurant_id` for tenant isolation
- Token refresh before expiry (at 75% usage)
- API keys for future POS integrations

### 2. restaurants Module
**Purpose:** Tenant/organization management.

**Key Components:**
- `models.py`: Restaurant, restaurant_settings (JSONB)
- `services.py`:
  - Create/get/update restaurant
  - Tenant validation
  - Settings management
- `routers.py`:
  - Admin restaurant CRUD endpoints

**Database Tables:** `restaurants`, `restaurant_settings`

### 3. branches Module
**Purpose:** Physical locations within a restaurant.

**Key Components:**
- `models.py`: Branch, branch settings
- `services.py`:
  - Branch creation under restaurant
  - Branch switching context
  - Deactivation (not deletion)
- `routers.py`:
  - Branch CRUD per restaurant

**Database Tables:** `branches`

### 4. staff Module
**Purpose:** Employees and role-based access control.

**Key Components:**
- `models.py`: Staff members, roles, permissions
- `services.py`:
  - Role creation with permission sets
  - Staff assignment to branches
  - Permission checking
- `routers.py`:
  - Role management endpoints
  - Staff assignment

**Design:**
- Roles are predefined (owner, manager, staff, viewer)
- Permissions are JSON flexible system
- Branch-level staff scoping

### 5. menus Module
**Purpose:** Menu definitions and versions.

**Key Components:**
- `models.py`: Menu, menu versions
- `services.py`:
  - Create menu for branch
  - Activate/deactivate menus
  - Version tracking
- `routers.py`:
  - Admin menu CRUD

**Design:**
- One active menu per branch at a time
- Multiple versions possible (lunch/dinner)
- Branding stored as JSON

### 6. categories Module
**Purpose:** Hierarchical menu categories.

**Key Components:**
- `models.py`: Category with parent_id (self-referential)
- `services.py`:
  - Category tree construction
  - Reordering (display_order)
  - Multilingual names (future)
- `routers.py`:
  - Category CRUD

**Design:**
- Unlimited depth (practical limit 5-6 levels)
- `display_order` for UI sorting
- `parent_id` null = root category

### 7. menu_items Module
**Purpose:** Individual food/drink items with customization.

**Key Components:**
- `models.py`: MenuItem, options, allergens
- `services.py`:
  - Item creation with options
  - Availability toggling
  - Popular/new flag management
  - Option validation
- `routers.py`:
  - Item CRUD with options management

**Design:**
- Prices in both Toman and Rial
- JSON `allergens_tags` for tags
- `item_options` relationship

### 8. tables Module
**Purpose:** Physical table management.

**Key Components:**
- `models.py`: Table, table status
- `services.py`:
  - Table assignment to orders
  - Status tracking (available, occupied, reserved, clean)
  - Capacity management
- `routers.py`:
  - Table CRUD per branch

**Design:**
- Status enum for workflow
- Branch scoping
- Real-time status updates

### 9. qr_codes Module
**Purpose:** QR code generation and tracking.

**Key Components:**
- `models.py`: QR code, target type/ID
- `services.py`:
  - QR code generation (SVG/PNG)
  - Context identification (restaurant/branch/table)
  - Expiration management
- `routers.py`:
  - Generate QR endpoints
  - QR status checks

**Design:**
- `target_type`: 'restaurant', 'branch', 'table'
- Image stored as URL (S3 or local)
- Usage tracking

### 10. customers Module
**Purpose:** Customer profiles and session management.

**Key Components:**
- `models.py`: Customer, profiles, anonymous tracking
- `services.py`:
  - Create anonymous session
  - Identified customer migration
  - Preference tracking
  - Session expiration
- `routers.py`:
  - Session creation/validation

**Design:**
- `is_anonymous` flag
- `external_id` for QR/mobile session ID
- Migration path to identified customer

### 11. orders Module
**Purpose:** Order lifecycle from creation to completion.

**Key Components:**
- `models.py`: Order, order_item
- `services.py`:
  - Order creation from cart
  - Status transition management
  - Item option validation
  - Total calculation
- `routers.py`:
  - Order creation API
  - Order status updates
  - Order items management

**Design:**
- Dual currency amounts
- Status enum workflow
- Option selection tracking

### 12. payments Module
**Purpose:** Payment provider abstraction and processing.

**Key Components:**
- `models.py`: Payment, transaction
- `services.py`:
  - Provider abstraction (Zarinpal, SMSPay)
  - Webhook handling
  - Payment status updates
  - Refund processing
- `routers.py`:
  - Payment initiation
  - Webhook endpoints
  - Payment status retrieval

**Abstraction Design:**
```python
class PaymentProvider(Protocol):
    def create_payment(self, amount, ...) -> PaymentResult: ...
    def verify_webhook(self, data) -> bool: ...
    def refund(self, payment_id, amount) -> bool: ...
```

Concrete implementations:
- `ZarinpalProvider` - Iranian payment gateway
- `SMSPayProvider` - SMS-based payment
- `MockProvider` - For testing

### 13. analytics Module
**Purpose:** Analytics calculation and reporting.

**Key Components:**
- `services.py`:
  - Metrics calculation from events
  - Conversion rate computation
  - Popular items/categories
  - Search analytics
- `routers.py`:
  - Analytics endpoints
  - Export functionality

**Data Sources:**
- `customer_events` table
- `orders` table
- `menu_items` table

### 14. events Module
**Purpose:** Customer event tracking pipeline.

**Key Components:**
- `services.py`:
  - Event validation and storage
  - Batch processing
  - Event type extensibility
  - Retention policies
- `routers.py`:
  - Event tracking API

**Design:**
- `event_type` as free string (extensible)
- Indexed fields for common queries
- JSON `metadata` for flexibility
- Async processing via Redis queue

### 15. recommendations Module
**Purpose:** Recommendation engine abstraction.

**Key Components:**
- `engine.py`: RecommendationEngine abstract base class
- `implementations/`:
  - `popular.py`: PopularItemsRecommendation
  - `content_based.py`: ContentBasedRecommendation
  - `collaborative.py`: CollaborativeFilteringRecommendation
- `schemas.py`: Recommendation schemas
- `routers.py`:
  - Generate recommendations API
  - Get recommendations for item

**Abstraction:**
```python
class RecommendationEngine(ABC):
    @abstractmethod
    def get_recommendations(
        self, 
        customer_id: int, 
        item_id: int, 
        limit: int = 5
    ) -> List[Recommendation]: ...
```

### 16. subscriptions Module
**Purpose:** SaaS billing and plan management.

**Key Components:**
- `models.py`: Subscription, invoice
- `services.py`:
  - Plan creation and management
  - Billing cycle handling
  - Feature flag enforcement
  - Upgrade/downgrade logic
- `routers.py`:
  - Subscription endpoints
  - Payment integration

**Plans:**
- Basic: Core menu features
- Pro: + Ordering, basic analytics
- Enterprise: + ML recommendations, advanced analytics

## Shared Utilities

### Database Base Mixin
```python
class BaseModel(Base):
    id: int = Field(default=None, primary_key=True)
    restaurant_id: int = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)
```

### Security Utilities
- Password hashing with Argon2
- JWT creation with `restaurant_id` subject
- Permission checking dependency
- Rate limiting middleware

### Logging Middleware
```python
@app.middleware("http")
async def add_request_id(request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    # Structured log
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        status=response.status_code,
        duration=response.headers.get("X-Process-Time"),
    )
    return response
```

## Background Job Processing

### Redis Queue (RQ or Celery)
**Jobs:**
- Payment provider webhook processing
- Email/SMS notifications
- Image optimization/resizing
- Recommendation calculation
- Analytics metric updates
- QR code expiry cleanup

**Queue Names:**
- `default` - General purpose
- `payments` - Payment processing
- `notifications` - Email/SMS
- `recommendations` - Rec engine jobs

## API Route Registration

### FastAPI App Factory
```python
def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Digital Menu API",
        version="1.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
    )
    
    # Register middleware
    app.add_middleware(...)
    
    # Include routers with prefix
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(public_router, prefix="/api/v1/public", tags=["public"])
    app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
    
    return app
```

## Dependency Injection Pattern

### Common Dependencies
```python
def get_db_session() -> Session:
    yield SessionLocal()

def get_current_user(
    db: Session = Depends(get_db_session),
    token: str = Depends(oauth2_scheme),
) -> User:
    # Validate JWT, check tenant, return user

def get_current_restaurant(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Restaurant:
    # Return restaurant based on user or JWT claim

def get_branch_context(
    branch_id: int = Query(...),
    current_restaurant: Restaurant = Depends(get_current_restaurant),
) -> Branch:
    # Validate branch belongs to restaurant
```

## Configuration Management

### Environment Variables (.env)
```
# App
APP_NAME=smart-digital-menu
APP_ENV=development|production
DEBUG=True|False

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sepehr
POSTGRES_USER=postgres
POSTGRES_PASSWORD=******

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Security
SECRET_KEY=******
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Payment Providers
ZARINPAL_MERCHANT_ID=******
ZARINPAL_CALLBACK_URL=http://...
SMSPAY_API_KEY=******

# OSS
MINIO_ENDPOINT=localhost:9000
MINIO_BUCKET=menu-images

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Development vs Production
- Development: SQLite for fast tests, Redis local
- Production: PostgreSQL, Redis, MinIO/S3
- Feature flags via environment
- CORS configuration per environment

## Testing Strategy

### pytest Configuration
- `conftest.py` with fixtures per module
- Database transaction rollback per test
- Test client for FastAPI

### Test Structure
```
tests/
  unit/
    test_auth.py
    test_restaurants.py
    test_menus.py
  integration/
    test_order_lifecycle.py
    test_customer_journey.py
  fixtures/
    conftest.py
```

### Key Test Areas
- Module isolation (each module testable independently)
- API response validation (Pydantic schemas)
- Database CRUD operations
- Authentication flows
- Event tracking completeness
- Recommendation engine swapping

## Migration Strategy (Alembic)

### Initial Migration (Phase 1)
- Core tables: users, restaurants, branches
- Auth tables

### Subsequent Migrations
- Phase 2: qr_codes, customer_sessions, customers
- Phase 3: orders, order_items, payments
- Phase 4: customer_events, favorites, reviews
- Phase 5: recommendations
- Phase 6: subscriptions

### Naming Convention
`v1_initial.py`, `v2_add_menus.py`, `v3_add_orders.py`, etc.

### Migration Testing
- `alembic upgrade head` in test environment
- Downgrade validation
- Data integrity checks