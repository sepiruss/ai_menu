# Smart Digital Menu Platform - Architecture Document

## Overview

This document describes the high-level architecture for the Smart Digital Menu platform, a multi-tenant SaaS product for restaurants and cafes in Iran. The system is designed as a **modular monolith** that can evolve into a microservices architecture if needed.

---

## Architectural Principles

### 1. Modular Monolith
- Single deployable application with clear domain boundaries
- Modules communicate via well-defined interfaces (not direct database access)
- Each module owns its data and exposes domain events
- Future extraction to microservices is possible without rewriting

### 2. Multi-Tenancy First
- Every business entity includes `restaurant_id` (tenant identifier)
- Row-level security policies enforce tenant isolation
- Shared database, shared schema approach with explicit tenant columns
- No cross-tenant data leakage possible at application or database level

### 3. Domain-Driven Design (DDD)
- Bounded contexts aligned with business domains
- Aggregates enforce consistency boundaries
- Domain events for cross-module communication
- Repository pattern for data access abstraction

### 4. Event-Driven Architecture
- Customer events are first-class citizens
- Event sourcing pattern for analytics and recommendations
- Async processing via background jobs
- Decoupled modules communicate via events

### 5. Mobile-First, API-First
- REST APIs designed for mobile consumers first
- Versioned APIs (`/api/v1/`)
- Separate public (customer) and admin (restaurant) API surfaces
- GraphQL considered for future flexibility

---

## System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SYSTEMS                         │
├─────────────┬─────────────┬─────────────┬───────────────────────┤
│  Payment    │   SMS       │   Cloud     │   Analytics/ML        │
│  Gateways   │  Providers  │  Storage    │   Platform (Future)   │
│  (Zarinpal, │  (Kavenegar,│  (S3/MinIO) │                       │
│   Mellat)   │   MeliPayamak)           │                       │
└──────┬──────┴──────┬──────┴──────┬─────┴───────────┬───────────┘
       │             │             │                 │
       ▼             ▼             ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SMART DIGITAL MENU                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   PUBLIC    │  │   ADMIN     │  │  INTERNAL   │             │
│  │   API       │  │   API       │  │  SERVICES   │             │
│  │  (Customer) │  │ (Restaurant)│  │             │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    CORE DOMAIN MODULES                    │   │
│  │  auth │ restaurants │ branches │ staff │ menus │ items  │   │
│  │  categories │ tables │ qr_codes │ customers │ sessions  │   │
│  │  orders │ payments │ analytics │ events │ recommendations│  │
│  │  subscriptions │ settings │ notifications               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                     │
│                          ▼                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   INFRASTRUCTURE LAYER                    │   │
│  │  PostgreSQL │ Redis │ Background Jobs │ File Storage     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Architecture

### Core Modules (Bounded Contexts)

| Module | Responsibility | Key Aggregates |
|--------|---------------|----------------|
| **auth** | Authentication, authorization, JWT tokens, API keys | User, Role, Permission, APIKey |
| **restaurants** | Restaurant onboarding, settings, branding, subscription | Restaurant, RestaurantSettings, Branding |
| **branches** | Physical locations, operating hours, address, contact | Branch, BranchSettings, OperatingHours |
| **staff** | Staff management, roles, permissions, shifts | StaffMember, StaffRole, Shift |
| **menus** | Menu lifecycle, versions, scheduling, publishing | Menu, MenuVersion, MenuSchedule |
| **categories** | Category hierarchy, ordering, visibility | Category, CategoryTranslation |
| **menu_items** | Items, pricing, options, allergens, availability | MenuItem, MenuItemOption, MenuItemTranslation |
| **tables** | Physical tables, QR codes, capacity, status | Table, TableQRCode, TableSession |
| **qr_codes** | QR generation, tracking, analytics | QRCode, QRScanEvent |
| **customers** | Customer profiles, preferences, loyalty | Customer, CustomerProfile, CustomerPreference |
| **customer_sessions** | Anonymous & authenticated sessions, device tracking | CustomerSession, DeviceInfo |
| **orders** | Order lifecycle, items, status, history | Order, OrderItem, OrderStatusHistory |
| **payments** | Payment processing, refunds, reconciliation | Payment, PaymentMethod, Transaction |
| **analytics** | Aggregated metrics, dashboards, reports | MetricSnapshot, Report, Dashboard |
| **events** | Customer event ingestion, processing, storage | CustomerEvent, EventProcessor |
| **recommendations** | Recommendation engine abstraction, strategies | RecommendationRequest, RecommendationResult |
| **subscriptions** | SaaS billing, plans, invoices, usage tracking | Subscription, Plan, Invoice, UsageRecord |
| **notifications** | SMS, push, email, in-app notifications | Notification, NotificationTemplate, Channel |

---

## Data Flow Patterns

### 1. Customer Menu Browsing (Read Path)
```
Customer scans QR
       │
       ▼
GET /api/v1/menu/{restaurant_slug}/{branch_slug}?table_id=xyz
       │
       ▼
Menu Module → Categories → Items (with availability, prices, images)
       │
       ▼
Returns optimized mobile response (cached in Redis)
```

### 2. Order Placement (Write Path)
```
POST /api/v1/orders
       │
       ▼
Validate items, availability, prices
       │
       ▼
Create Order (PENDING) → Reserve inventory (if applicable)
       │
       ▼
Publish OrderCreatedEvent
       │
       ├──→ Payments Module: Initiate payment
       ├──→ Kitchen/Staff: Notify new order
       ├──→ Analytics: Increment counters
       └──→ Events: Store ORDER_CREATED event
```

### 3. Event Ingestion (Async)
```
Customer action (view, click, add-to-cart)
       │
       ▼
POST /api/v1/events/batch
       │
       ▼
Validate & enrich with context (session, restaurant, branch)
       │
       ▼
Write to customer_events table (append-only)
       │
       ▼
Publish to Redis Stream / Message Queue
       │
       ├──→ Real-time Analytics Processor
       ├──→ Recommendation Feature Store Updater
       └──→ ML Training Data Pipeline (Future)
```

---

## Technology Stack

### Backend
| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.11+ |
| Framework | FastAPI | 0.109+ |
| Validation | Pydantic | 2.6+ |
| ORM | SQLAlchemy | 2.0+ |
| Migrations | Alembic | 1.13+ |
| Database | PostgreSQL | 16+ |
| Cache/Queue | Redis | 7.2+ |
| Background Jobs | Celery | 5.3+ |
| Testing | pytest | 7.4+ |
| Async HTTP | httpx | 0.26+ |

### Frontend
| Component | Technology | Version |
|-----------|------------|---------|
| Framework | Next.js | 14+ (App Router) |
| Language | TypeScript | 5.3+ |
| Styling | Tailwind CSS | 3.4+ |
| UI Components | shadcn/ui | Latest |
| State Management | Zustand / React Query | Latest |
| Forms | React Hook Form + Zod | Latest |
| i18n | next-intl | Latest |

### Infrastructure
| Component | Technology |
|-----------|------------|
| Containerization | Docker, docker-compose |
| Reverse Proxy | Nginx / Traefik |
| SSL | Let's Encrypt / Cert-manager |
| Monitoring | Prometheus + Grafana |
| Logging | Structured JSON (structlog) |
| Error Tracking | Sentry (optional) |

---

## Security Architecture

### Authentication
- **JWT Access Tokens**: Short-lived (15 min), signed RS256
- **Refresh Tokens**: Long-lived (30 days), rotated, stored hashed in DB
- **API Keys**: For server-to-server, restaurant integrations
- **Anonymous Sessions**: Device-fingerprint based, no PII

### Authorization
- **RBAC**: Role-Based Access Control (Owner, Manager, Staff, Waiter)
- **ABAC**: Attribute-Based for fine-grained (branch-level, menu-level)
- **Tenant Isolation**: Middleware enforces `restaurant_id` on every request

### Data Protection
- **Encryption at Rest**: PostgreSQL TDE / column-level for PII
- **Encryption in Transit**: TLS 1.3 everywhere
- **PII Minimization**: No unnecessary personal data collected
- **GDPR/Privacy Ready**: Right to deletion, data export endpoints

### API Security
- **Rate Limiting**: Per-IP, per-customer, per-restaurant (Redis-backed)
- **CORS**: Strict origin validation
- **Input Validation**: Pydantic on all inputs
- **SQL Injection**: SQLAlchemy ORM + parameterized queries only
- **File Uploads**: Type validation, size limits, virus scan (future)

---

## Observability

### Structured Logging
```json
{
  "timestamp": "2026-09-02T10:30:00.123Z",
  "level": "INFO",
  "request_id": "req_abc123",
  "restaurant_id": "rest_123",
  "user_id": "user_456",
  "module": "orders",
  "action": "create_order",
  "duration_ms": 45,
  "status": "success"
}
```

### Health Endpoints
- `GET /health/live` - Liveness (process alive)
- `GET /health/ready` - Readiness (DB, Redis, dependencies)
- `GET /health/metrics` - Prometheus metrics

### Distributed Tracing
- Request ID propagated through all services
- OpenTelemetry ready for future adoption

---

## Deployment Architecture

### Local Development
```yaml
# docker-compose.yml
services:
  postgres:  # Primary database
  redis:     # Cache, sessions, job queue
  backend:   # FastAPI application
  frontend:  # Next.js application
  celery:    # Background workers
  nginx:     # Reverse proxy (optional)
```

### Production (Conceptual)
```
                    ┌─────────────┐
                    │   CDN/WAF   │  (Cloudflare, CloudFront)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Load Balancer │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │ Backend  │     │ Backend  │     │ Backend  │  (Auto-scaling group)
    │ Pod 1    │     │ Pod 2    │     │ Pod N    │
    └────┬─────┘     └────┬─────┘     └────┬─────┘
         │                │                │
         └────────────────┼────────────────┘
                          ▼
              ┌───────────────────────┐
              │   PostgreSQL Primary  │
              │   + Read Replicas     │
              └───────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       ┌────────────┐          ┌────────────┐
       │   Redis    │          │   Object   │
       │  Cluster   │          │  Storage   │
       └────────────┘          └────────────┘
```

---

## Cross-Cutting Concerns

### Configuration Management
- Environment variables via `pydantic-settings`
- Separate `.env` files per environment
- Secrets via Docker secrets / HashiCorp Vault (production)

### Database Migrations
- Alembic for versioned migrations
- Migration per module (separate revision directories)
- Backward-compatible migrations only
- CI/CD runs migrations before deploy

### Background Job Processing
- Celery with Redis broker
- Priority queues: `high`, `default`, `low`
- Scheduled tasks via Celery Beat
- Dead letter queue for failed jobs

### Caching Strategy
- **L1**: In-memory (LRU) for hot data
- **L2**: Redis for shared cache
- **Cache Keys**: `module:entity:id:version`
- **Invalidation**: Event-driven + TTL fallback

---

## Future Extensibility

### Module Extraction Path
When a module needs independent scaling:
1. Extract module to separate repository
2. Define gRPC/REST contract
3. Deploy as independent service
4. Update API Gateway routing
5. Migrate data (if needed)

### ML Platform Integration
- Feature store built on customer_events
- Model serving via separate inference service
- A/B testing framework for recommendations
- Real-time feature computation via Flink/Spark (future)

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-09-02 | Modular monolith over microservices | Team size, operational simplicity, lower latency |
| 2026-09-02 | Shared DB schema with tenant columns | Simpler operations, strong consistency, lower cost |
| 2026-09-02 | Event-driven analytics foundation | Enables ML later, real-time dashboards, audit trail |
| 2026-09-02 | Separate public/admin APIs | Different auth, rate limits, evolution paths |
| 2026-09-02 | Celery over native async for jobs | Reliability, retries, scheduling, monitoring |

---

## Appendix: Module Communication Contracts

### Domain Events (Published)
```python
# Example: OrderCreatedEvent
{
  "event_type": "ORDER_CREATED",
  "event_id": "evt_uuid",
  "timestamp": "2026-09-02T10:30:00Z",
  "restaurant_id": "rest_123",
  "branch_id": "branch_456",
  "payload": {
    "order_id": "order_789",
    "customer_id": "cust_abc",
    "session_id": "sess_xyz",
    "items": [...],
    "total_amount": 500000
  }
}
```

### Module Interfaces (Internal)
```python
# Each module exposes a service class
class MenuService:
    async def get_menu_for_customer(
        self, 
        restaurant_id: UUID, 
        branch_id: UUID, 
        table_id: UUID | None
    ) -> MenuResponse: ...

class OrderService:
    async def create_order(
        self, 
        cmd: CreateOrderCommand
    ) -> Order: ...
```

---

*End of Architecture Document*