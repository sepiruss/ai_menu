# Smart Digital Menu - Database Design

## Overview
Normalized relational schema for PostgreSQL supporting multi-tenancy, Persian locale, and future ML/recommendation features.

## Entity Relationship Diagram (Mermaid)

```mermaid
erDiagram
    %% Core Tenancy
    USERS ||--|{ RESTAURANTS : "owns"
    RESTAURANTS ||--|{ BRANCHES : "has"
    BRANCHES ||--|{ TABLES : "has"
    BRANCHES ||--|{ MENUS : "has"
    BRANCHES ||--|{ ORDERS : "processes"
    
    %% Authentication
    USERS {
        bigint id PK
        varchar(255) email UNIQUE
        varchar(255) password_hash
        varchar(100) role
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    
    RESTAURANTS {
        bigint id PK
        varchar(255) name
        varchar(255) slug UNIQUE
        varchar(255) timezone
        boolean is_active
        jsonb settings
        bigint owner_id FK > USERS
        timestamp created_at
        timestamp updated_at
    }
    
    BRANCHES {
        bigint id PK
        bigint restaurant_id FK > RESTAURANTS
        varchar(255) name
        varchar(255) code UNIQUE
        jsonb settings
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }
    
    TABLES {
        bigint id PK
        bigint branch_id FK > BRANCHES
        varchar(50) name
        varchar(50) code
        integer capacity
        boolean is_active
        jsonb layout_config
        timestamp created_at
        timestamp updated_at
    }
    
    %% Menu System
    MENUS {
        bigint id PK
        bigint branch_id FK > BRANCHES
        varchar(255) name
        boolean is_active
        boolean is_default
        jsonb branding
        timestamp published_at
        timestamp created_at
        timestamp updated_at
    }
    
    CATEGORIES {
        bigint id PK
        bigint menu_id FK > MENUS
        bigint parent_id FK > CATEGORIES
        varchar(255) name
        varchar(255) slug
        integer display_order
        boolean is_visible
        jsonb translation
        timestamp created_at
        timestamp updated_at
    }
    
    MENU_ITEMS {
        bigint id PK
        bigint category_id FK > CATEGORIES
        varchar(255) name
        text description
        decimal price_toman
        decimal price_rial
        boolean is_available
        boolean is_popular
        boolean is_new
        integer display_order
        jsonb metadata
        jsonb allergens_tags
        timestamp created_at
        timestamp updated_at
    }
    
    MENU_ITEM_OPTIONS {
        bigint id PK
        bigint menu_item_id FK > MENU_ITEMS
        varchar(255) name
        decimal price_adjustment
        boolean is_required
        integer display_order
        jsonb options_config
        timestamp created_at
    }
    
    %% Tables and QR
    QR_CODES {
        bigint id PK
        bigint branch_id FK > BRANCHES
        varchar(255) code_image_url
        varchar(255) code_type
        varchar(255) target_type  -- 'restaurant'|'branch'|'table'
        bigint target_id FK
        string status
        timestamp created_at
        timestamp expires_at
    }
    
    %% Customers
    CUSTOMERS {
        bigint id PK
        bigint restaurant_id FK > RESTAURANTS
        varchar(255) external_id  -- mobile or web session ID
        varchar(255) phone_number
        jsonb preferences
        boolean is_anonymous
        timestamp created_at
        timestamp last_active_at
    }
    
    CUSTOMER_SESSIONS {
        bigint id PK
        bigint customer_id FK > CUSTOMERS
        varchar(255) session_token UNIQUE
        varchar(255) fingerprint
        jsonb metadata
        timestamp started_at
        timestamp last_accessed_at
        timestamp expires_at
    }
    
    %% Orders
    ORDERS {
        bigint id PK
        bigint branch_id FK > BRANCHES
        bigint customer_id FK > CUSTOMERS
        varchar(255) status  -- 'pending', 'confirmed', 'preparing', 'ready', 'completed', 'cancelled'
        decimal total_toman
        decimal total_rial
        varchar(100) payment_status
        jsonb payment_method
        timestamp ordered_at
        timestamp completed_at
        timestamp cancelled_at
    }
    
    ORDER_ITEMS {
        bigint id PK
        bigint order_id FK > ORDERS
        bigint menu_item_id FK > MENU_ITEMS
        integer quantity
        decimal price_per_item_toman
        decimal price_per_item_rial
        jsonb options_selected
        jsonb modifications
        integer display_order
    }
    
    %% Payments
    PAYMENTS {
        bigint id PK
        bigint order_id FK > ORDERS
        varchar(50) provider  -- 'zarinpal', 'smspay', 'manual'
        varchar(255) provider_reference
        varchar(50) status  -- 'pending', 'paid', 'failed', 'refunded'
        decimal amount_toman
        decimal amount_rial
        timestamp initiated_at
        timestamp completed_at
        timestamp created_at
    }
    
    %% Customer Events (Critical)
    CUSTOMER_EVENTS {
        bigint id PK
        bigint customer_id FK > CUSTOMERS
        bigint restaurant_id FK > RESTAURANTS
        bigint branch_id FK > BRANCHES
        bigint menu_item_id FK > MENU_ITEMS
        bigint category_id FK > CATEGORIES
        varchar(50) event_type
        jsonb metadata
        timestamp created_at
    }
    
    %% Favorites
    FAVORITES {
        bigint id PK
        bigint customer_id FK > CUSTOMERS
        bigint menu_item_id FK > MENU_ITEMS
        timestamp created_at
        UNIQUE(customer_id, menu_item_id)
    }
    
    %% Reviews
    REVIEWS {
        bigint id PK
        bigint customer_id FK > CUSTOMERS
        bigint branch_id FK > BRANCHES
        bigint menu_item_id FK > MENU_ITEMS
        integer rating
        text comment
        boolean is_approved
        timestamp created_at
        timestamp updated_at
    }
    
    %% Recommendations
    RECOMMENDATIONS {
        bigint id PK
        bigint menu_item_id FK > MENU_ITEMS
        bigint restaurant_id FK > RESTAURANTS
        varchar(50) recommendation_type  -- 'popular', 'content_based', 'collaborative'
        decimal confidence_score
        jsonb reasoning
        integer rank_position
        timestamp created_at
    }
    
    %% Subscriptions
    SUBSCRIPTIONS {
        bigint id PK
        bigint restaurant_id FK > RESTAURANTS
        varchar(50) plan_type
        varchar(50) status
        decimal amount_toman
        jsonb features
        timestamp started_at
        timestamp current_period_end
        timestamp cancel_at
    }
    
    %% Restaurant Settings
    RESTAURANT_SETTINGS {
        bigint id PK
        bigint restaurant_id FK > RESTAURANTS
        jsonb general_settings
        jsonb branding
        jsonb locale
        jsonb currency
        timestamp updated_at
    }
    
    %% Roles and Permissions
    ROLES {
        bigint id PK
        varchar(50) name UNIQUE
        jsonb permissions
        timestamp created_at
    }
    
    STAFF_MEMBERS {
        bigint id PK
        bigint branch_id FK > BRANCHES
        bigint user_id FK > USERS
        bigint role_id FK > ROLES
        boolean is_active
        timestamp created_at
    }
```

## Table Descriptions

### 1. users
- System users (restaurant owners, staff, admin)
- Stores hashed passwords and roles
- One user can own multiple restaurants

### 2. restaurants
- Tenant/organization entity
- Each restaurant has its own branches, menus, settings
- `restaurant_id` cascades to all child entities

### 3. branches
- Physical locations within a restaurant
- Each branch has its own tables, menus, QR codes
- Supports restaurant chains

### 4. tables
- Physical tables at each branch
- Used for order tracking and server management
- Capacity indicates max guests

### 5. menus
- Menu versions per branch
- Supports multiple menus (lunch, dinner, seasonal)
- `is_default` marks the active menu

### 6. categories
- Hierarchical categories (self-referential parent_id)
- Deep nesting support for complex menus
- Multilingual `translation` JSON field

### 7. menu_items
- Individual food/drink items
- Prices in both Toman and Rial
- Supports allergens/tags via JSON
- Popular/new flags for UI display

### 8. menu_item_options
- Customization options (size, spice level, extra toppings)
- Price adjustments tracked
- Required vs optional options

### 9. qr_codes
- QR codes for restaurant, branch, or table
- `target_type` discriminates context
- Expiration support for temporary QR codes

### 10. customers
- Customer profiles (anonymous or identified)
- `external_id` tracks QR session or mobile ID
- `is_anonymous` flag for privacy
- Preferences stored as JSON

### 11. customer_sessions
- Active session tracking
- Fingerprint for bot detection
- Automatic expiration

### 12. orders
- Order lifecycle tracking
- Dual currency amounts (Toman/RIAL)
- Payment status tracking

### 13. order_items
- Line items within orders
- JSON for selected options/modifications
- Quantity tracking

### 14. payments
- Payment provider abstraction
- Provider reference for external tracking
- Amount in both currencies

### 15. customer_events **(CRITICAL)**
- Flexible event tracking system
- `event_type` is a free string ( extensible)
- Indexed fields for common analytics queries
- JSON `metadata` for arbitrary context

### 16. favorites
- User favorited items
- Unique constraint per customer-item pair

### 17. reviews
- Customer reviews for items/branches
- Rating and text comment
- Approval workflow

### 18. recommendations
- Stored recommendations for UI
- Recommendation type tracking
- Confidence scores for ML later

### 19. subscriptions
- SaaS pricing plans per restaurant
- Plan features via JSON
- Billing period tracking

### 20. roles
- RBAC system
- JSON permissions for flexibility

### 21. staff_members
- Branch-level staff assignments
- Role-based permissions

## Indexing Strategy

### Critical Indexes for Analytics:
```sql
CREATE INDEX idx_customer_events_type ON customer_events(event_type);
CREATE INDEX idx_customer_events_created ON customer_events(created_at);
CREATE INDEX idx_customer_events_restaurant ON customer_events(restaurant_id);
CREATE INDEX idx_customer_events_menu_item ON customer_events(menu_item_id);
CREATE INDEX idx_customer_events_customer ON customer_events(customer_id);
CREATE INDEX idx_customer_events_branch ON customer_events(branch_id);
```

### Frequently Queried:
```sql
CREATE INDEX idx_orders_branch_status ON orders(branch_id, status);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_menu_items_category_available ON categories_id, is_available;
CREATE INDEX idx_customers_restaurant_anonymous ON restaurant_id, is_anonymous;
```

## Multi-Tenancy Implementation

### Approach: Schema-Plus with restaurant_id
- All tables have `restaurant_id` column (nullable for shared data)
- Application layer enforces restaurant context per request
- No separate databases/schemas per tenant initially (simpler)
- Can partition later if needed

### Tenant Resolution:
1. JWT contains `restaurant_id`
2. Middleware sets `current_restaurant_id`
3. All queries filter by `current_restaurant_id`
4. Branch-scoped queries also filter by `branch_id`

## Currency Handling

### Price Storage:
- `price_toman`: Primary pricing (Iranian Toman)
- `price_rial`: Secondary (1 Toman = 10 Rial)
- Both stored as `DECIMAL(15, 2)`
- UI displays based on restaurant configuration

### Example:
- Item price: 50,000 Toman = 5,000,000 Rial
- Stored as: price_toman = 50000.00, price_rial = 500000.00

## Jalali Date Support

### Application-Level:
- Dates stored as UTC timestamps in PostgreSQL
- Formatted to Jalali in the frontend (Next.js)
- No Jalali type in PostgreSQL (use VARCHAR or custom extension)
- Key dates tracked: `created_at`, `updated_at`, `ordered_at`, `completed_at`

## Future-Proofing for ML

### Recommendation Data:
- `recommendations` table stores generated recommendations
- `customer_events` provides behavioral data
- `favorites` and `reviews` indicate explicit preferences
- `order_items` shows purchase patterns

### Data Available for Future ML:
- Customer view history (events)
- Purchase history (orders + order_items)
- Item popularity metrics
- Time-based patterns (hour, day of week)
- Similar customer behavior (via events)