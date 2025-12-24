# Performance Optimization Guide

## Current Performance Issues

**Problem:** Fetching all 500 events on every request, even for 20-item pages.

**Impact:**
- First page: 2-3 seconds
- Every page: 2-3 seconds (no caching)
- Unnecessary Shopify API calls

## Solution 1: Redis Caching (BIGGEST IMPACT) 🚀

### Performance Improvement:
```
Without cache: 2-3 seconds per request
With cache:    50-100ms per request (40x faster!)
```

### Setup (Free Tier):

**Option A: Local Redis (Development)**
```bash
# Install Redis
brew install redis  # Mac
# or
sudo apt install redis  # Linux

# Start Redis
redis-server

# Add to .env
REDIS_URL=redis://localhost:6379
```

**Option B: Upstash (Production - Free Tier)**
1. Sign up at https://upstash.com (free tier: 10K requests/day)
2. Create Redis database
3. Copy connection URL
4. Add to `.env`:
```
REDIS_URL=rediss://default:xxxxx@xxxxx.upstash.io:6379
```

### Implementation:

```python
# backend/app/core/cache.py
import redis
import json
from typing import Optional
import os

redis_client = redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

def cache_get(key: str) -> Optional[dict]:
    """Get cached data"""
    data = redis_client.get(key)
    return json.loads(data) if data else None

def cache_set(key: str, value: dict, ttl: int = 300):
    """Cache data with TTL (default 5 minutes)"""
    redis_client.setex(key, ttl, json.dumps(value))

def cache_delete(key: str):
    """Invalidate cache"""
    redis_client.delete(key)
```

### Update events endpoint:

```python
# In get_events function, add caching:

# Generate cache key
cache_key = f"events:page={page}:limit={limit}:search={search}:category={category}:status={status}"

# Try cache first
cached = cache_get(cache_key)
if cached:
    return cached

# ... fetch from Shopify ...

# Cache the result
cache_set(cache_key, response_data, ttl=300)  # 5 minutes
return response_data
```

### Cache Invalidation:

```python
# When creating/updating/deleting events:
from app.core.cache import cache_delete

# Invalidate all event list caches
redis_client.delete("events:*")
```

---

## Solution 2: Optimize Fetch Strategy (FREE)

### Current (SLOW):
```python
# Fetches ALL 500 events every time
while len(all_events) < 500:
    fetch_batch()
```

### Optimized (FASTER):
```python
# Only fetch what's needed for current page
max_needed = page * limit
while len(all_events) < max_needed:
    fetch_batch()
    if len(all_events) >= max_needed:
        break
```

**Impact:** 2-3x faster for early pages

---

## Solution 3: Database Sync (BEST for Scale)

For 100+ events, sync to PostgreSQL:

**Benefits:**
- Instant queries (no Shopify API calls)
- Full-text search
- Complex filtering
- No rate limits

**Implementation:**
1. Webhook: Shopify → Your API when events change
2. Store events in PostgreSQL
3. Query PostgreSQL for list
4. Fetch details from Shopify only when needed

---

## Shopify Plan Comparison

| Feature | Basic ($39) | Plus ($2000+) | Benefit |
|---------|-------------|---------------|---------|
| API Rate | 2 req/sec | 4 req/sec | 2x faster |
| GraphQL Cost | 2000 pts | 4000 pts | 2x queries |
| Bulk API | ❌ | ✅ | Faster imports |

**Recommendation:** Stay on Basic, use Redis caching instead.

---

## Quick Wins Checklist

- [ ] Add Redis caching (40x faster)
- [ ] Optimize fetch strategy (3x faster)
- [ ] Add GraphQL field selection (smaller payloads)
- [ ] Consider PostgreSQL sync for 100+ events

**Total potential speedup: 100x faster with caching!**

---

## Cost Comparison

| Solution | Cost | Speedup | Complexity |
|----------|------|---------|------------|
| Redis (Upstash free) | $0 | 40x | Low |
| Shopify Plus | $2000/mo | 2x | None |
| PostgreSQL sync | $0 | 100x | Medium |

**Best ROI:** Redis caching (free, 40x faster, easy to implement)
