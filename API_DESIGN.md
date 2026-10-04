# Smart Digital Menu - API Design

## Overview
RESTful API with versioning `/api/v1/`. Separation between public customer APIs and admin restaurant APIs.

## Base Configuration
- Base URL: `/api/v1/`
- JSON content-type
- UTF-8 encoding
- Persian/RTL support headers where applicable
- Query parameter encoding: `UTF-8`

## Authentication

### JWT Authentication
- Login endpoint returns JWT access token (15min expiry)
- Refresh token endpoint for new access tokens (30day expiry)
- Token included in: `Authorization: Bearer <token>` header

### API Key (for third-party integrations)
- Separate key system for POS integrations, etc.

### Public Endpoints (No Auth)
- Menu browsing, search
- QR code validation
- Customer session creation

### Protected Endpoints
- All order/ payment/ admin endpoints require valid JWT

## API Versioning
- Current: `v1`
- Future: `v2` when breaking changes needed
- Version in URL path: `/api/v1/...`
- Deprecation policy: 6 months notice, `Deprecation` header

## Error Format
```json
{
  "error": "ERROR_TYPE",
  "message": "Human readable message",
  "details": {...},
  "request_id": "uuid-string"
}
```
HTTP status codes:
- 400: Bad request (validation errors)
- 401: Unauthorized
- 403: Forbidden (tenant mismatch, wrong role)
- 404: Not found
- 422: Unprocessable entity
- 429: Too many requests
- 500: Internal server error

## Public Customer APIs

### Menu Browsing

#### GET /api/v1/public/menus
List menus for a branch.
- Query: `branch_id`, `status` (default: active)
- Response: list of menus with basic info

#### GET /api/v1/public/menus/{menu_id}
Get menu details.
- Path: `menu_id`
- Response: full menu with categories and items

#### GET /api/v1/public/menus/{menu_id}/categories
Get categories for a menu.
- Path: `menu_id`
- Query: `parent_id` (optional)
- Response: category hierarchy

#### GET /api/v1/public/menus/{menu_id}/categories/{category_id}/items
Get items in a category.
- Path: `menu_id`, `category_id`
- Query: `search`, `popular`, `new`, `available_only`
- Response: paginated menu items

#### GET /api/v1/public/menus/{menu_id}/items/search
Search items.
- Query: `q` (search term), `category_id`
- Response: matching items

### Item Details

#### GET /api/v1/public/menus/{menu_id}/items/{item_id}
Get item details.
- Path: `item_id`
- Response: item with options, allergens, images

#### GET /api/v1/public/menus/{menu_id}/items/{item_id}/options
Get item customization options.

### QR and Session

#### POST /api/v1/public/qr/scan
Create/continue customer session via QR.
- Body: `qr_code_id`, `branch_id`
- Response: `customer_id`, `session_token`, `is_anonymous`

#### GET /api/v1/public/sessions/{session_token}
Get customer session info.

### Analytics (Public)

#### POST /api/v1/public/events
Track customer event.
- Body: `event_type`, `menu_item_id`, `category_id`, `metadata`
- Response: 202 Accepted (no return needed)

## Admin Restaurant APIs

### Authentication
- Admin users belong to restaurants
- Role-based access control
- Each admin has `restaurant_id` context

### Restaurant Management

#### GET /api/v1/admin/restaurants
List restaurants (super admin only).

#### GET /api/v1/admin/restaurants/{restaurant_id}
Get restaurant details.

#### PUT /api/v1/admin/restaurants/{restaurant_id}
Update restaurant info.

### Branch Management

#### GET /api/v1/admin/restaurants/{restaurant_id}/branches
List branches.

#### POST /api/v1/admin/restaurants/{restaurant_id}/branches
Create branch.

#### GET /api/v1/admin/restaurants/{restaurant_id}/branches/{branch_id}
Get branch details.

#### PUT /api/v1/admin/restaurants/{restaurant_id}/branches/{branch_id}
Update branch.

#### DELETE /api/v1/admin/restaurants/{restaurant_id}/branches/{branch_id}
Delete branch (soft delete).

### Menu Management

#### GET /api/v1/admin/menus
List menus for branch.

#### POST /api/v1/admin/menus
Create new menu.

#### GET /api/v1/admin/menus/{menu_id}
Get menu with items.

#### PUT /api/v1/admin/menus/{menu_id}
Update menu.

#### DELETE /api/v1/admin/menus/{menu_id}
Soft delete menu.

#### POST /api/v1/admin/menus/{menu_id}/items
Create menu item.

#### PUT /api/v1/admin/menus/{menu_id}/items/{item_id}
Update menu item.

#### DELETE /api/v1/admin/menus/{menu_id}/items/{item_id}
Soft delete menu item.

### Category Management

#### GET /api/v1/admin/categories
List all categories.

#### POST /api/v1/admin/categories
Create category.

#### PUT /api/v1/admin/categories/{category_id}
Update category.

### Order Management

#### GET /api/v1/admin/orders
List orders for branch.
- Query: `status`, `date_from`, `date_to`, `customer_id`

#### GET /api/v1/admin/orders/{order_id}
Get order details.

#### GET /api/v1/admin/orders/{order_id}/items
Get order items.

### Payment Management

#### GET /api/v1/admin/payments
List payments.

#### GET /api/v1/admin/payments/{payment_id}
Get payment details.

### Customer Management

#### GET /api/v1/admin/customers
List customers for branch.
- Query: `is_anonymous`, `date_range`

#### GET /api/v1/admin/customers/{customer_id}
Get customer details.

### Event Tracking (Admin)

#### GET /api/v1/admin/events
List events with filtering.
- Query: `event_type`, `customer_id`, `branch_id`, `menu_item_id`, `date_range`

### Recommendations

#### GET /api/v1/admin/recommendations
List recommendations.

#### POST /api/v1/admin/recommendations
Generate recommendations.

#### GET /api/v1/public/recommendations/{item_id}
Get recommended items for a menu item (public).

### Subscriptions

#### GET /api/v1/admin/subscriptions
List restaurant subscriptions.

#### GET /api/v1/admin/subscriptions/{subscription_id}
Get subscription details.

## File Upload APIs

#### POST /api/v1/upload/image
Upload menu item image.
- Headers: `Content-Type: image/*`
- Size limit: 10MB
- Returns: `image_url`

#### POST /api/v1/upload/logo
Upload restaurant logo.

## Webhook Endpoints (POST, no auth in traditional sense)

#### POST /api/v1/webhooks/payment
Payment provider webhook (Zarinpal, SMSPay).
- Signature verification via header
- Idempotent processing

#### POST /api/v1/webhooks/sms
SMS provider delivery receipts.

## Rate Limiting

### Per-Endpoint Limits
- Public menu: 200 req/min per IP
- Authenticated: 100 req/min per token
- Admin: 50 req/min per user
- Event tracking: 50 req/min per customer

### Headers
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

## OpenAPI/Swagger
- `/api/v1/docs` - Swagger UI
- `/api/v1/redoc` - ReDoc
- Machine-readable schema at `/api/v1/openapi.json`