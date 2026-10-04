# Smart Digital Menu - Recommendation Architecture

## Overview
Abstraction layer for food/drink recommendations that evolves from simple popularity-based to advanced ML models without changing public API.

## Core Design Principle
**API Stability**: The public recommendation API remains constant regardless of underlying implementation.
**Swapability**: Engines can be swapped at runtime via configuration.
**Extensibility**: New algorithms added without modifying consumer code.

## RecommendationEngine Abstraction

### Abstract Base Class
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel

class Recommendation(BaseModel):
    menu_item_id: int
    rank: int
    score: float
    reason: str  # Human-readable reason for recommendation

class RecommendationEngine(ABC):
    """Abstract base class for all recommendation engines."""
    
    @abstractmethod
    def get_recommendations(
        self,
        customer_id: Optional[int],
        restaurant_id: int,
        branch_id: Optional[int] = None,
        exclude_item_ids: Optional[List[int]] = None,
        limit: int = 5,
        context: Optional[dict] = None
    ) -> List[Recommendation]:
        """Get recommendations for a customer or context.
        
        Args:
            customer_id: Anonymous or identified customer ID
            restaurant_id: Target restaurant for tenant isolation
            branch_id: Specific branch (optional)
            exclude_item_ids: Items to exclude (e.g., already ordered)
            limit: Maximum number of recommendations
            context: Additional context (time, day, party size, etc.)
            
        Returns:
            List of Recommendation objects ranked by relevance
        """
        pass
    
    @abstractmethod
    def get_similar_items(
        self,
        menu_item_id: int,
        limit: int = 5,
        context: Optional[dict] = None
    ) -> List[Recommendation]:
        """Find items similar to a given item.
        
        Useful for "Also served with" or "Customers also ordered" sections.
        """
        pass
    
    @abstractmethod
    def update_feedback(
        self,
        customer_id: int,
        menu_item_id: int,
        feedback: str  # 'viewed', 'clicked', 'ordered', 'ignored'
    ) -> None:
        """Update engine with user feedback for learning."""
        pass
```

### Engine Implementations

#### 1. PopularItemsRecommendation (Phase 5 Initial)
**Strategy**: Items ordered most frequently across the restaurant.

```python
class PopularItemsRecommendation(RecommendationEngine):
    def get_recommendations(self, customer_id, restaurant_id, ..., limit=5, ...):
        # Query most popular items from database
        # Filter by restaurant, exclude already-ordered items
        # Return top 'limit' items with rank and basic score
        
    def get_similar_items(self, menu_item_id, limit=5, ...):
        # Based on co-occurrence in orders
        # Customers who ordered this also ordered...
```

**Data Sources:**
- `orders` + `order_items` tables
- Real-time popularity counts
- Branch-level popularity

**Score Formula:**
```
score = (order_count * weight_recency) + (avg_rating * weight_quality)
```

**Pros:** 
- Immediate implementation possible
- No ML dependencies
- Understandable by restaurant owners
- Works from day one

**Cons:**
- No personalization
- Popular items only (not tailored)
- Global, not customer-specific

#### 2. ContentBasedRecommendation
**Strategy**: Recommend items based on item characteristics and customer preferences.

**Feature Vector:**
- Item attributes: category, price range, popularity tags
- Customer history: viewed items, favorited items, order history
- Weighted matching between preferences and item features

**Algorithm:**
1. Build customer preference profile from `customer_events` + `favorites` + `orders`
2. Score all restaurant items against profile
3. Return top-N unviewed/ordered items

**Data Sources:**
- `customer_events` (view, click patterns)
- `favorites` table
- `orders` + `order_items`
- `menu_items` attributes (category, price, tags)

**Use Case:**
- "Items similar to ones you've viewed"
- "Recommend based on your preferences"

#### 3. CollaborativeFilteringRecommendation
**Strategy**: Find similar customers and recommend what they ordered.

**Two Approaches:**
- **User-User**: Find customers with similar behavior, recommend their items
- **Item-Item**: Find items frequently ordered together

**Algorithm (Simplified):**
1. Build interaction matrix: customers × items (views, orders)
2. Compute similarity between customers or items
3. Find items rated highly by similar customers/items
4. Recommend un-interacted items

**Data Sources:**
- `customer_events` (requires sufficient data)
- `orders` + `order_items` (purchase history)
- `favorites` (explicit preferences)

**Maturity Level:**
- Needs minimum data threshold (e.g., 100+ active customers)
- Sparse matrix problem (most customers order few items)
- Regularization required

#### 4. HybridRecommendation
**Strategy**: Combine multiple approaches for best results.

**Combination Strategies:**
- **Weighted Average**: `score = w1*popular + w2*content + w3*collaborative`
- **Conditional**: Use popular as fallback when collaborative has low confidence
- **Switching**: Select best engine based on data availability

**Example Implementation:**
```python
class HybridRecommendation(RecommendationEngine):
    def __init__(self, engines: dict, weights: dict):
        self.engines = engines  # {'popular': ..., 'content': ..., 'collaborative': ...}
        self.weights = weights  # {'popular': 0.5, 'content': 0.3, 'collaborative': 0.2}
    
    def get_recommendations(self, customer_id, restaurant_id, ...):
        recommendations = {}
        
        # Run all engines
        for name, engine in self.engines.items():
            recs = engine.get_recommendations(customer_id, restaurant_id, ...)
            for rec in recs:
                if rec.menu_item_id not in recommendations:
                    recommendations[rec.menu_item_id] = {'score': 0, 'engines': []}
                recommendations[rec.menu_item_id]['score'] += rec.score * self.weights[name]
                recommendations[rec.menu_item_id]['engines'].append(name)
        
        # Sort by combined score
        sorted_recs = sorted(recommendations.items(), key=lambda x: x[1]['score'], reverse=True)
        return [Recommendation(menu_item_id=mid, rank=i+1, score=data['score'], reason=f"{' + '.join(data['engines'])}") 
                for i, (mid, data) in enumerate(sorted_recs[:limit])]
```

#### 5. MLRecommendation (Phase 6+)
**Strategy**: scikit-learn / LightGBM / PyTorch models.

**Data Pipeline:**
1. Feature engineering from `customer_events`, `orders`, `menu_items`
2. Train model to predict rating/probability
3. Generate top-N recommendations per customer

**Potential Models:**
- **LightGBM**: Tree-based, fast, handles sparse data well
- **implicit**: Matrix factorization for collaborative filtering
- **PyTorch DeepFM**: Factorization Machine + Deep Neural Network
- **scikit-learn**: Baseline models (RandomForest, GradientBoosting)

**Feature Engineering:**
```
Customer Features:
- total_orders
- total_spent
- favorite_categories
- viewed_categories
- time_of_day_preference
- day_of_week_preference

Item Features:
- category
- price_range
- popularity_score
- view_count
- order_count
- allergen_tags

Context Features:
- hour_of_day
- day_of_week
- season
- party_size
- location (branch)
```

**Training Data Construction:**
- Positive examples: items ordered by customer
- Negative examples: items not ordered (sampled)
- Context features per interaction

**Model Serving:**
- Train offline (nightly or weekly)
- Export model to ONNX or pickle
- Fast inference (<50ms per recommendation)
- Cache results for popular customers

## API Design (Public)

### Endpoints

#### GET /api/v1/public/recommendations/{menu_item_id}
Get recommendations for a menu item.
- Query: `customer_id` (optional), `limit` (default: 5)
- Response:
```json
{
  "recommendations": [
    {
      "menu_item_id": 42,
      "rank": 1,
      "score": 0.85,
      "reason": "Popular item this season"
    }
  ],
  "engine": "popular",  // which engine was used
  "generated_at": "2024-01-15T10:30:00Z"
}
```

#### GET /api/v1/public/recommendations/
Get personalized recommendations.
- Query: `customer_id`, `restaurant_id`, `limit`, `exclude`
- Response same structure as above

#### POST /api/v1/admin/recommendations
Generate/update recommendations.
- Body: `engine_type`, `customer_id` (optional), `item_id` (optional)
- Triggers engine calculation

### Engine Configuration

```yaml
# config/recommendations.yaml
engine: hybrid
engines:
  popular:
    enabled: true
    weight: 0.5
  content_based:
    enabled: true  
    weight: 0.3
  collaborative:
    enabled: false  # requires minimum data
    weight: 0.2
  ml:
    enabled: false  # requires training
    weight: 0.0
    
data_thresholds:
  collaborative_min_customers: 100
  ml_min_interactions: 1000

update_schedule:
  popular: "hourly"
  content_based: "daily"
  collaborative: "daily"
  ml: "weekly"
```

## Extensibility Pattern

### Adding a New Engine

1. **Create new class** implementing `RecommendationEngine`
2. **Register in factory**:
```python
def get_recommendation_engine(engine_type: str) -> RecommendationEngine:
    engines = {
        'popular': PopularItemsRecommendation(),
        'content_based': ContentBasedRecommendation(),
        'collaborative': CollaborativeFilteringRecommendation(),
        'hybrid': HybridRecommendation(...),
        'ml': MLRecommendation(),
    }
    return engines.get(engine_type, PopularItemsRecommendation())
```

3. **Update config** to enable/disable
4. **Deploy** - no API changes needed

### Adding New Event Types for Recommendations

The `customer_events` table uses free-form `event_type`. New types can be added:

```sql
-- No migration needed for new event types
-- Just use in engine logic

INSERT INTO customer_events (event_type, ...) VALUES ('RECOMMENDATION_ACCEPTED', ...)
```

Engine implementations can listen for:
- `ITEM_VIEW` - Build preference profile
- `ITEM_CLICK` - Stronger preference signal
- `ITEM_ORDER` - Gold standard for training
- `ITEM_FAVORITE` - Explicit preference
- `ITEM_SEARCH` - Interest indication

## Data Requirements Progression

| Engine | Minimum Data | Optimal Data | Time to Implement |
|--------|-------------|--------------|-------------------|
| PopularItems | 1 restaurant | Any | 1 day |
| ContentBased | 50 customers | 200+ | 1 week |
| CollaborativeFiltering | 100 customers | 500+ | 2 weeks |
| MLRecommendation | 1000 customers | 5000+ | 4-6 weeks |

## Implementation Roadmap

### Phase 5 (Week 1-2): Popular Items
- [x] `RecommendationEngine` abstract class
- [x] `PopularItemsRecommendation` implementation
- [x] `recommendations` table
- [x] API endpoints `/api/v1/public/recommendations/{item_id}`
- [x] Admin generation endpoint
- [x] Frontend recommendation display

### Phase 6 (Week 3-6): Content-Based + Collaborative
- [ ] `ContentBasedRecommendation` implementation
- [ ] Feature engineering from existing data
- [ ] Collaborative filtering baseline
- [ ] `HybridRecommendation` engine
- [ ] Data thresholds configuration
- [ ] A/B testing framework

### Phase 7 (Week 7-10): ML Integration
- [ ] Feature pipeline construction
- [ ] Model training infrastructure
- [ ] LightGBM or implicit model
- [ ] ONNX export for inference
- [ ] Shadow mode (ML alongside popular, compare results)
- [ ] Gradual rollout % control

### Ongoing: Engine Swapping
- [ ] Configuration-driven engine selection
- [ ] Canopy tests for each engine
- [ ] Performance monitoring (latency, accuracy)
- [ ] A/B testing framework for CTR impact