# Smart Digital Menu - Development Roadmap

## Product Phases

### Phase 1: Foundation + Authentication + Restaurant + Branch + Menu + Categories + Items
**Duration:** 6-8 weeks

**Core Goals:**
- Multi-tenant SaaS foundation
- Authentication and authorization
- Restaurant and branch management
- Basic menu system (categories + items)
- Admin dashboard for CRUD operations
- PostgreSQL database with multi-tenancy
- Alembic migrations
- Basic FastAPI setup

**Deliverables:**
- User authentication (JWT, roles)
- Restaurant CRUD
- Branch CRUD per restaurant
- Category management
- Menu item CRUD
- Basic API endpoints
- Database schema (as designed)
- Alembic migration setup
- Docker development environment

**Key Tables (Phase 1):**
- users, restaurants, branches, categories, menu_items

---

### Phase 2: Customer Mobile Menu + QR
**Duration:** 4-6 weeks

**Core Goals:**
- Mobile-first digital menu UI
- QR code generation and scanning
- Anonymous customer sessions
- Menu browsing without account
- Persian RTL support
- Mobile responsive design

**Deliverables:**
- Next.js frontend with RTL support
- QR code generation endpoint
- Customer session management
- Mobile menu UI (categories, items, search)
- QR codes for restaurant, branch, table
- Public API for menu browsing

**Key Additions:**
- qr_codes table
- customer_sessions table
- Anonymous customer support
- Mobile menu UI

---

### Phase 3: Ordering + Tables
**Duration:** 6-8 weeks

**Core Goals:**
- Order creation from customer mobile menu
- Table assignment and management
- Order items customization via options
- Order status tracking
- Integration with Phase 1-2 foundations

**Deliverables:**
- Order creation API
- Order item customization
- Table status tracking
- Order lifecycle (pending → confirmed → preparing → ready → completed)
- Modifiers and options for items
- Kitchen order display (basic)

**Key Additions:**
- orders table
- order_items table
- table status management
- Order customization via menu_item_options

---

### Phase 4: Events + Analytics
**Duration:** 4-5 weeks

**Core Goals:**
- Customer event tracking (CRITICAL)
- Analytics dashboard foundation
- Metrics: views, searches, conversion, popular items
- Event pipeline to Redis/background jobs
- Exportable analytics data

**Deliverables:**
- customer_events table (as designed)
- Event tracking API
- Analytics dashboard data
- Conversion rate calculations
- Popular items/categories tracking
- Search analytics

**Key Additions:**
- customer_events table
- Analytics reporting endpoints
- Event processing pipeline

---

### Phase 5: Recommendation Engine
**Duration:** 4-5 weeks

**Core Goals:**
- Abstraction for recommendation engines
- Popular items-based initial implementation
- Recommendation API endpoints
- Stored recommendations in database
- A/B testing framework possibility

**Deliverables:**
- RecommendationEngine abstraction
- PopularItemsRecommendation implementation
- API: GET /recommendations/{item_id}
- Recommendations table
- Integration with customer events

**Key Additions:**
- recommendations table
- Recommendation engine abstraction
- Popular-based recommendations

---

### Phase 6: ML Recommendation
**Duration:** 6-8 weeks (ongoing)

**Core Goals:**
- ML model training infrastructure
- scikit-learn / LightGBM integration (optional)
- Collaborative filtering prototypes
- Hybrid recommendation strategies
- Model versioning and A/B testing

**Deliverables:**
- ML pipeline infrastructure
- Multiple recommendation strategies
- Model performance tracking
- Gradual rollout framework

**Potential Technologies:**
- scikit-learn (for initial ML)
- LightGBM (gradient boosting)
- implicit (matrix factorization)
- PyTorch (deep learning, future)

**Note:** Dependencies added only when Phase 5 is validated.

---

### Phase 7: SaaS Billing/Subscriptions + Advanced Analytics
**Duration:** 4-6 weeks

**Core Goals:**
- Subscription plans per restaurant
- Tiered pricing (Basic, Pro, Enterprise)
- Advanced analytics dashboards
- Revenue tracking
- Invoice generation
- Feature flags per plan tier

**Deliverables:**
- Subscriptions table
- Payment integration (Zarinpal, SMSPay)
- Plan-based feature limits
- Advanced reporting
- Revenue analytics
- Billing cycle management

**Key Additions:**
- subscriptions table
- Payment providers integration
- Feature flag system

---

## Phase Gate Reviews

Each phase ends with:
1. Feature demo to stakeholder
2. Code review
3. Test coverage validation
4. Performance benchmarking
5. Decision: continue, pivot, or adjust scope

## Risk Mitigation Per Phase

| Phase | Risk | Mitigation |
|-------|------|------------|
| 1 | Multi-tenancy design flaws | Early isolation testing, data segregation verification |
| 2 | QR scan reliability | Multiple QR format support, fallback mechanisms |
| 3 | Order loss/duplication | Idempotent order creation, duplicate detection |
| 4 | Event data gaps | Comprehensive event types, validation on every interaction |
| 5 | Recommendation quality | A/B testing framework, easy algorithm swapping |
| 7 | Billing complexity | Abstraction layer, provider agnosticism |

## Success Metrics Per Phase

- **Phase 1**: 100% test coverage on core modules, API docs generated
- **Phase 2**: Mobile menu usability score > 4/5, QR scan success > 95%
- **Phase 3**: Order completion rate > 80%, customization success > 90%
- **Phase 4**: Event tracking 100% coverage for documented types, analytics data fresh
- **Phase 5**: Recommendation CTR > 5% in A/B test
- **Phase 6**: ML model improves CTR by > 2x over popularity baseline
- **Phase 7**: Subscription conversion > 20%, billing accuracy > 99.9%