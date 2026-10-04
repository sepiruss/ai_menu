# Smart Digital Menu - Frontend Structure

## Overview
Next.js 14+ with App Router, TypeScript, Tailwind CSS, shadcn/ui.
Mobile-first, Persian RTL support, future English/Arabic i18n.

## Project Structure
```
sepehr-frontend/
  src/
    /app/                    # Next.js App Router
      /(public)/             # Public routes (no auth)
        /                    # Landing page
        /menu/[branch_id]    # Customer menu route
        /qr/[code]           # QR code landing
        /auth                # Auth routes (login, etc.)
      /(dashboard)/          # Protected dashboard routes
        /restaurants         # Restaurant list (super admin)
        /[restaurant_id]     # Restaurant dashboard
          /branches          # Branch management
          /menus             # Menu management
          /orders            # Order view
          /analytics         # Analytics dashboard
          /settings          # Restaurant settings
      /layout.tsx            # Root layout with i18n/provider
      /page.tsx              # Homepage
      
    /components/             # React components
      /ui/                   # shadcn/ui primitives
        button.tsx
        input.tsx
        dialog.tsx
        table.tsx
        dropdown-menu.tsx
        badge.tsx
        avatar.tsx
        rtl-provider.tsx     # RTL toggle
        
      /menu/                 # Menu-related components
        /category-card.tsx
        /item-card.tsx
        /item-options.tsx
        /search-bar.tsx
        /filter-chip.tsx
        /popular-badge.tsx
        /new-badge.tsx
        /favorite-icon.tsx
        
      /order/               # Order-related components
        /order-summary.tsx
        /cart-modal.tsx
        /table-selector.tsx
        /order-status.tsx
        
      /shared/              # Shared UI components
        /language-switcher.tsx
        /currency-display.tsx
        /loading-spinner.tsx
        /error-boundary.tsx
        
      /dashboard/           # Admin dashboard components
        /category-form.tsx
        /item-form.tsx
        /table-manager.tsx
        /qr-generator.tsx
        /analytics-charts.tsx
        
    /layouts/               # Page layouts
      /rtl-layout.tsx       # Persian RTL layout
      /ltr-layout.tsx       # English layout
      
    /pages/               # Pages (app router alternative)
      /login.tsx
      /register.tsx
      
    /contexts/            # React Context providers
      /AuthContext.tsx      # User auth state
      /RestaurantContext.tsx # Current restaurant/branch
      /ThemeContext.tsx     # Light/dark/RTL
      
    /hooks/               # Custom React hooks
      /use-menu.ts          # Menu browsing hook
      /use-order.ts         # Order management hook
      /use-events.ts        # Event tracking hook
      /use-recommendations.ts
      /use-translation.ts   # i18n hook
      /use-debounce.ts
      /use-scroll.tsx
      
    /lib/                 # Utilities
      /api-client.ts        # Axios instance with auth
      /utils.ts             # General helpers
      /currency.ts          # Toman/Rial formatting
      /date.ts              # Jalali date formatting
      /ql.ts               # Query string utils
      
    /types/               # TypeScript types
      /api.ts               # API response types
      /menu.ts              # Menu domain types
      /order.ts             # Order domain types
      /customer.ts          # Customer types
      
    /services/            # Service modules
      /menu.service.ts      # Menu API calls
      /order.service.ts     # Order API calls
      /auth.service.ts      # Auth API calls
      /event.service.ts     # Event tracking
      /recommendation.service.ts
      
    /constants/           # Constants
      /event-types.ts
      /routes.ts
      /currency.ts
      
    /styles/              # Global styles
      /globals.css          # Tailwind base
      /rtl.css              # RTL overrides
      /responsive.ts        # Breakpoints
      
    /i18n/                # Internationalization
      /messages/
        /en.json
        /fa.json          # Persian
        /ar.json          # Arabic (future)
      /next-i18next-config.js
      
    /utils/               # Additional utils
      /form-validation.ts
      /debounce.ts
  
  /public/                # Static assets
    /favicon.ico
    /og-image.png
  
  next.config.js          # Next.js config
  tailwind.config.js       # Tailwind config
  tsconfig.json           # TypeScript config
  .env.local              # Local environment
  .env.production         # Production environment
```

## Key Design Decisions

### 1. App Router Structure
- `/(public)` - Customer-facing routes (no auth)
- `/(dashboard)` - Restaurant admin routes (auth required)
- Root layout provides `RestaurantContext` and `ThemeProvider`

### 2. RTL Support (Persian)
- `rtl-layout.tsx` wraps components with `dir="rtl"`
- Tailwind `rtl:direction` utilities where needed
- `LanguageContext` toggles between LTR/RTL
- Persian font family (Vazirmatn, Nasim, etc.)
- Numbers formatted without commas in Persian

### 3. Mobile-First Design
- Tailwind breakpoints: `sm`, `md`, `lg`, `xl`
- Hamburger navigation on mobile
- Touch-friendly tap targets (minimum 48px)
- Swipe gestures for carousel/categories
- Responsive grid for items (1-4 columns)

### 4. shadcn/ui Integration
- Custom components from shadcn/ui base
- Consistent design system across app
- Accessible by default (ARIA labels)
- Dark mode support via `class` strategy

### 5. Internationalization (i18n)
- Next.js `next-i18next` or `react-i18next`
- Default: Persian (`fa`)
- Additional: English (`en`), Arabic (`ar`) future
- JSON message files per language
- Date/currency formatting per locale

### 6. API Client
```typescript
// src/lib/api-client.ts
import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 10000,
  withCredentials: true, // for cookies/auth
});

// Request interceptor for request ID
api.interceptors.request.use((config) => {
  const requestId = crypto.randomUUID();
  config.headers["X-Request-Id"] = requestId;
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle auth errors, etc.
    return Promise.reject(error);
  }
);

export default api;
```

### 7. Menu Browsing Flow

**Customer Journey:**
1. Scan QR → opens `/menu/[branch_id]`
2. Menu loads with categories
3. User browses categories → sees items
4. User searches or filters
5. User adds items to "cart" (local state)
6. User proceeds to order
7. Table selection → order creation via API
8. Order status tracked in real-time

### 8. Component Hierarchy

**Menu Page:**
```
MenuPage
  ├── LanguageSwitcher
  ├── SearchBar
  ├── FilterChips (popular, new, available)
  ├── CategoryTabs
  │    ├── CategoryCard
  │    └── ItemGrid
  │         ├── ItemCard
  │         │    ├── Image
  │         │    ├── Name
  │         │    ├── Price (Toman/Rial)
  │         │    ├── FavoriteIcon
  │         │    ├── Badge (popular/new)
  │         │    └── OptionsButton
  │         └── AddToCartButton
  └── CartSummary
```

**Admin Dashboard:**
```
DashboardLayout
  ├── Sidebar (navigation)
  ├── TopBar (user, notifications)
  └── ContentArea
       ├── PageHeader
       ├── FormComponent (create/edit)
       ├── Table/ListView
       └── ActionButtons
```

### 9. State Management

**Local State (useState):**
- Form values
- Component-level UI state
- Cart items (local until checkout)

**Global State (Context):**
- `AuthContext`: User, restaurant, branch
- `ThemeContext`: Light/dark/RTL
- `LanguageContext`: Locale
- `CartContext`: Order cart (could use React Query instead)

**Data Fetching (React Query):**
- Menu data (staleTime: 5min)
- Restaurant info
- Customer profile
- Order status polling
- Analytics data

### 10. Form Handling

**Schema Validation:**
- Yup or Zod for forms
- Pydantic on backend
- Client-side validation + server confirmation

**Form Components:**
- `shadcn/ui` Input, Select, Textarea
- Custom components for:
  - Image upload with preview
  - Color picker (for branding)
  - Date picker (Jalali support)
  - Rating component

### 11. Image Upload

**Workflow:**
1. User selects image file
2. Preview before upload
3. Upload to MinIO/S3 via presigned URL
4. Image validation (size, type, dimensions)
5. Optimize/resize on server
6. Store `image_url` in database
7. Display optimized image in UI

**Validation:**
- Max 10MB
- Types: jpeg, png, webp
- Dimensions: square preferred for items
- Compression if > 2MB

### 12. Order Flow

**Step-by-Step:**
1. Browse menu → add items to cart
2. Select table number
3. Review order summary
4. Choose payment method
5. Submit order → API `/api/v1/public/orders`
6. Receive order ID
7. Track order status (polling/WebSocket)
8. Order completion confirmation

### 13. Event Tracking

**Client-Side Events:**
```typescript
// src/hooks/use-events.ts
export function useEventTracking() {
  const track = async (eventType: string, metadata?: any) => {
    await api.post("/api/v1/public/events", {
      event_type: eventType,
      ...metadata,
      customer_id: customerId,
      restaurant_id: restaurantId,
      branch_id: branchId,
      session_id: sessionId,
      timestamp: new Date().toISOString(),
    });
  };
  
  return { track };
}
```

**Automatic Tracking:**
- `onMenuView`
- `onCategoryView`
- `onItemView`
- `onAddToCart`
- `onRemoveFromCart`
- `onOrderComplete`

### 14. Recommendations UI

**Recommendation Display:**
```
RecommendedSection
  ├── Title ("Recommended for you" / "Popular items")
  ├── Scrollable carousel
  ├── ItemCard (with recommendation badge)
  └── See all link
```

**Source:**
- Popular items (backend API)
- "Also served with" (item relations)
- Customer's previous interactions

### 15. Analytics Dashboard (Admin)

**Charts & Metrics:**
- Menu views over time (line chart)
- Item views (bar chart)
- Search volume (bar)
- Add-to-cart rate (donut)
- Conversion rate (funnel)
- Popular items table
- Popular categories table
- Recommendation CTR

**Data Source:**
- Backend `/api/v1/admin/events` API
- Aggregated from `customer_events` table
- Real-time updates via WebSocket (future)

### 16. QR Code Generation

**QR Page:**
```
/qr/[code]
```
- Reads QR code target from database
- Identifies: restaurant, branch, or table
- Shows appropriate context
- For tables: shows "Order at table X" CTA
- For restaurant: shows general menu

**Backend QR Service:**
- Generate SVG/PNG QR
- Store target_type and target_id
- Return URL path `/qr/[code]`

## Performance Optimizations

### Image Optimization
- Next.js `next/image` for automatic optimization
- WebP/AVIF formats
- Lazy loading for all images
- CDN for static assets

### Code Splitting
- Route-based code splitting (Next.js automatic)
- Component-level dynamic imports
- Vendors separated (React, React Query)

### Caching Strategy
- React Query `cacheTime: 30min`
- Stale-while-revalidate for menu data
- Static generation for restaurant listings

### Bundle Optimization
- Terser minification
- Purge unused CSS (Tailwind JIT)
- Analyze with `next-bundle-analyzer`

## Accessibility (a11y)

- Semantic HTML (heading order, labels)
- Keyboard navigation (Tab order, Escape modals)
- Screen reader support (ARIA labels, roles)
- Color contrast (minimum 4.5:1)
- Focus visible states
- RTL accessibility (text direction, icon mirroring)

## Security Considerations

### XSS Prevention
- Escape user-generated content (menu descriptions, reviews)
- Sanitize image uploads
- Content-Security-Policy headers

### CSRF Protection
- SameSite cookies
- Anti-CSRF tokens for state-changing forms
- Double-submit cookie pattern

### Data Validation
- Zod schema validation on all forms
- Backend Pydantic validation
- Input length limits
- SQL injection prevention (SQLAlchemy ORM)

### Tenant Isolation
- Every API call includes `restaurant_id`
- Frontend context maintains current restaurant
- URL parameters validated against user context

## Environment Differences

### Development
- `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`
- Mock data for offline development
- Source maps enabled
- Hot module replacement

### Production
- `NEXT_PUBLIC_API_URL=https://api.your-domain.com/api/v1`
- Optimized bundle (`next build`)
- CDN assets
- Error tracking (Sentry integration)
- Analytics (plausible/self-hosted)

## Recommended Development Order (Frontend)

1. **Week 1-2**: Layout, RTL support, basic theming, language switcher
2. **Week 3-4**: Menu browsing components (categories, items, search)
3. **Week 5-6**: QR scanning flow, customer session, cart
4. **Week 7-8**: Order flow, table selection, payment integration
5. **Week 9-10**: Admin dashboard skeleton (CRUD forms)
6. **Week 11-12**: Analytics charts, recommendations UI
7. **Week 13+**: Polish, performance, accessibility, internationalization