# Smart Digital Menu

A modern, Iran-first Smart Digital Menu SaaS platform for restaurants and cafes. Customers scan QR codes to browse menus, add items to cart, and place orders directly from their phones.

## Features

- **QR Code Based Ordering** - Customers scan QR codes on tables to access the menu
- **Multi-tenant Architecture** - Supports multiple restaurants, branches, and tables
- **Full Menu Management** - Categories, items, options, pricing in Toman/Rial
- **Shopping Cart** - Add items, customize with options, manage quantities
- **Order Management** - Create orders, track status (PENDING → CONFIRMED → PREPARING → READY → SERVED)
- **Real-time Events** - Track customer interactions (menu views, item views, searches)
- **Persian/RTL Support** - Full RTL layout with Vazirmatn font
- **Mobile-First Design** - Optimized for mobile browsers
- **JWT Authentication** - Secure admin access with role-based permissions

## Tech Stack

- **Backend**: FastAPI (Python 3.11+), SQLAlchemy 2.0, PostgreSQL 16, Redis 7
- **Frontend**: Vanilla JavaScript, Tailwind CSS, Vazirmatn font (Persian RTL)
- **Database**: PostgreSQL 16 with Alembic migrations
- **Cache/Queue**: Redis 7
- **Deployment**: Docker Compose

## Project Structure

```
sepehrProject/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── core/           # Core config, database, security, middleware
│   │   ├── models/         # SQLAlchemy models
│   │   └── modules/        # Feature modules (auth, restaurants, menus, etc.)
│   ├── alembic/            # Database migrations
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # Static frontend (mobile-first)
│   ├── index.html
│   ├── src/
│   │   ├── app.js         # Main application logic
│   │   └── styles.css     # Custom styles + Tailwind
│   └── public/
├── docs/                   # Documentation
├── docker-compose.yml      # Local development stack
├── .gitignore
└── README.md
```

## Prerequisites

- Docker Desktop with WSL2 integration
- Git
- (Optional) Python 3.11+ for local development without Docker

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/sepiruss/ai_menu.git
cd ai_menu
```

### 2. Start Infrastructure

```bash
cd backend
docker compose up -d postgres redis
```

Wait for services to be healthy:
```bash
docker compose ps
# Both postgres and redis should show "healthy"
```

### 3. Run Migrations

```bash
cd alembic
python -m alembic upgrade head
```

### 4. Seed Demo Data (Optional)

```bash
python seed_docker.py
```

This creates:
- Demo user: `demo@example.com` / `demo123456` (superuser)
- Demo restaurant with 5 tables
- Full menu with 4 categories and 13 items
- 5 QR codes (one per table)

### 5. Start Backend

```bash
cd ..
docker compose up -d backend
```

Backend will be available at: **http://localhost:8000**

### 6. Start Frontend

```bash
cd ../frontend
python -m http.server 3000
```

Frontend will be available at: **http://localhost:3000**

## Demo Flow

1. Open http://localhost:3000
2. Click "ورود به منو" (Enter Menu) - uses demo session
3. Browse categories: پیش‌غذا، غذای اصلی، نوشیدنی، دسر
4. Click any item to see details (price, description, options)
5. Click "افزودن به سبد" to add to cart
6. Click cart icon (top-right) to view cart
7. Adjust quantities, remove items
8. Click "ثبت سفارش" to create order
9. View order confirmation with order number

### Test with QR Code

Use any of these QR tokens in the URL:
```
http://localhost:3000/?qr=w63BBr7hsl-5nCH2fcfBZam0bfAQ6xHhl510f4fMiaU
http://localhost:3000/?qr=dmtslTjHg-VjU0FFlRgSQl2HeoTW3aHD1wyYCs-A4Bg
http://localhost:3000/?qr=px3uxL3TAyv9Jqy38eafJhaoQ16zz3ONAa61lCu08iM
```

## API Documentation

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

### Key Endpoints

#### Public (Customer-facing)
- `POST /api/v1/public/qr/{token}` - Resolve QR code, create session
- `GET /api/v1/public/menu/{branch_id}` - Get full menu with categories
- `GET /api/v1/public/menu/{branch_id}/items` - Get items by category
- `GET /api/v1/public/menu/{branch_id}/items/{item_id}` - Get item details
- `POST /api/v1/public/cart/items` - Add item to cart
- `GET /api/v1/public/cart` - Get current cart
- `PUT /api/v1/public/cart/items/{item_id}` - Update cart item
- `DELETE /api/v1/public/cart/items/{item_id}` - Remove item
- `POST /api/v1/public/orders` - Create order from cart
- `GET /api/v1/public/orders` - List orders
- `POST /api/v1/public/orders/{id}/cancel` - Cancel order

#### Admin (Requires Authentication)
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/admin/restaurants` - List restaurants
- `POST /api/v1/admin/restaurants` - Create restaurant
- `GET /api/v1/admin/branches` - List branches
- `GET /api/v1/admin/menus` - List menus
- `POST /api/v1/admin/qr-codes` - Create QR codes

## Development

### Local Development (without Docker)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your local database URL
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

### Running Tests

```bash
cd backend
pytest -v
```

## Database Migrations

```bash
cd backend/alembic

# Create new migration
python -m alembic revision --autogenerate -m "description"

# Apply migrations
python -m alembic upgrade head

# Rollback one migration
python -m alembic downgrade -1
```

## Seeding Data

```bash
# Development seed (local)
cd backend/alembic && python seed.py

# Docker seed (production-like)
python seed_docker.py
```

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://smart_menu:smart_menu_dev@localhost:5432/smart_menu` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Required |
| `ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | 15 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | 30 |
| `ENVIRONMENT` | Environment | development |

## Database Schema

Key tables:
- `users` - Admin users with roles (superuser, owner, admin, manager)
- `restaurants` - Restaurant entities
- `branches` - Restaurant branches
- `tables` - Physical tables with QR codes
- `menus` - Menus per branch
- `categories` - Hierarchical categories
- `menu_items` - Menu items with pricing (Toman/Rial)
- `menu_item_options` - Item customization options
- `qr_codes` - QR codes linked to tables
- `customers` - Anonymous customer profiles
- `customer_sessions` - Active browsing sessions
- `customer_events` - Analytics events
- `carts` / `cart_items` - Shopping carts
- `orders` / `order_items` - Orders with status tracking

## Deployment

### Production Considerations

1. **Change SECRET_KEY** - Generate a strong 32+ character key
2. **Use strong database passwords**
3. **Enable HTTPS** with reverse proxy (nginx/traefik)
4. **Configure CORS_ORIGINS** for production domain
5. **Set ENVIRONMENT=production**
6. **Use managed PostgreSQL/Redis** (AWS RDS, ElastiCache, etc.)
6. **Set up monitoring** (Prometheus, Grafana)
7. **Configure backups** for PostgreSQL

### Docker Production Build

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL container is healthy: `docker compose ps`
- Check DATABASE_URL format: `postgresql+asyncpg://user:pass@host:port/db`
- Verify network connectivity between containers

### Migration Issues
```bash
# Reset migrations (development only)
cd backend/alembic
python -m alembic downgrade base
python -m alembic upgrade head
```

### Frontend Not Loading
- Ensure frontend server is running on port 3000
- Check browser console for CORS errors
- Verify backend CORS_ORIGINS includes frontend URL

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## Support

For issues and feature requests, please use GitHub Issues.