# Smart Digital Menu - Architecture Documentation

## Overview
A production-quality Smart Digital Menu platform for restaurants and cafes, initially targeting Iran. The system follows a **modular monolith** architecture that enables future extraction of modules into independent services.

## Core Principles

### 1. Modular Monolith
- Single deployed unit, clear internal module boundaries
- Each module (domain) has its own directory, models, routes, services
- Modules can be extracted to microservices later without changing public API
- Shared infrastructure (database, Redis, caching) within one process

### 2. Multi-Tenancy (SaaS)
- Each restaurant = one tenant
- Explicit `restaurant_id` on most business entities
- Tenant isolation at application level (not database-per-tenant initially)
- Branch-level partitioning within a restaurant

### 3. Directory Structure (Backend)
```
src/
  auth/           # Authentication module
  restaurants/    # Restaurant management
  branches/       # Branch/location management
  staff/          # Staff members and roles
  menus/          # Menu management
  categories/     # Menu categories
  menu_items/     # Individual menu items
  tables/         # Table management
  qr_codes/       # QR code generation
  customers/      # Customer management
  customer_sessions/ # Session tracking
  orders/         # Order management
  payments/       # Payment processing
  analytics/      # Analytics module
  events/         # Customer event tracking
  recommendations/# Recommendation engine
  subscriptions/  # SaaS billing
  shared/         # Shared utilities, constants, etc.
```

### 4. API Design Philosophy
- RESTful APIs with versioning: `/api/v1/...`
- Separate public (customer) and admin APIs
- JSON:API-like structure where appropriate
- Query parameters for filtering, pagination, sorting

### 5. Data Flow
```
Customer Browser --> QR Code --> /api/v1/public/menu --> HTML Response
                          --> /api/v1/public/events --> Event Tracking
                          --> /api/v1/public/orders --> Order Creation
Admin Dashboard --> /api/v1/admin/... --> Restaurant Management
```

### 6. Technology Stack Decisions
- **Python 3.11+** with FastAPI
- **SQLAlchemy 2.0** with async support
- **PostgreSQL** 15+ for relational data
- **Redis** for caching, sessions, and background jobs
- **Alembic** for database migrations
- **Pydantic** for request/response validation (v2)
- **pytest** for testing

### 7. Internationalization
- Default: Persian (Farsi) with RTL layout
- Next.js/i18n routing for future English/Arabic
- Date formatting: Jalali (Persian) calendar
- Currency: Iranian Toman (primary) / Rial (secondary)

### 8. Background Job Architecture
- Redis-backed job queue (e.g., RQ or Celery)
- Webhook handlers for payment providers
- Email/SMS notification processing
- Event processing pipeline

### 9. Security Model
- JWT-based authentication for API
- Role-based access control (RBAC)
- Tenant isolation validation on every protected endpoint
- Rate limiting per API key/tenant
- Input validation via Pydantic
- SQL injection prevention via SQLAlchemy ORM
- Secure file uploads with virus scanning
- CORS configuration per environment
- CSRF protection for state-changing endpoints

### 10. Observability
- Structured JSON logging (correlation IDs)
- Request tracking middleware
- Health checks: `/health`, `/api/v1/health`
- Database connection pool monitoring
- Redis connectivity checks
- Error tracking and reporting

## Module Boundaries

| Module | Responsibility | Key Entities |
|--------|---------------|--------------|
| auth | User auth, sessions, API keys | users, api_keys, refresh_tokens |
| restaurants | Tenant/organization management | restaurants, restaurant_settings |
| branches | Restaurant locations | branches, branch_settings |
| staff | Employees and permissions | staff_members, roles, permissions |
| menus | Menu definitions | menus, menu_versions |
| categories | Category hierarchy | categories, category_order |
| menu_items | Individual menu items | menu_items, item_options, allergens |
| tables | Physical tables | tables, table_status |
| qr_codes | QR code generation | qr_codes, qr_usage |
| customers | Customer profiles | customers, customer_profiles |
| customer_sessions | Active sessions | customer_sessions, session_tokens |
| orders | Order lifecycle | orders, order_items, orders |
| payments | Payment processing | payments, payment_transactions |
| analytics | Metrics and reporting | analytics_events, dashboards |
| events | Event tracking | customer_events |
| recommendations | Food recommendations | recommendations, rec_history |
| subscriptions | SaaS billing | subscriptions, invoices |