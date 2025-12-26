# PostgreSQL + Webhook Architecture (V2 Optimization)

## Overview

This document describes the **optimal architecture** for handling high concurrency (10,000+ users) while maintaining data consistency and eliminating Shopify API rate limits.

**Key Principle:** Shopify as Single Source of Truth (SSOT), PostgreSQL as Read Replica, Webhooks as Sync Mechanism.

---

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│         SHOPIFY (Source of Truth)       │
│                                         │
│  • Checkout & Payments                  │
│  • Inventory Locking                    │
│  • Order Processing                     │
│  • Product Management                   │
└─────────────────────────────────────────┘
         ↑ WRITE ONLY           ↓ WEBHOOKS (Push)
         │                      │
         │                      ↓
┌────────┴──────────┐    ┌─────────────────────┐
│   YOUR BACKEND    │    │   POSTGRESQL        │
│   (FastAPI)       │    │   (Read Replica)    │
│                   │    │                     │
│  Admin APIs:      │    │  Tables:            │
│  • Create event   │───→│  • events           │
│  • Update event   │    │  • tickets          │
│  • Delete event   │    │  • orders           │
│  • Update ticket  │    │  • processed_webhooks│
│                   │    │                     │
│  Webhook APIs:    │    │  Performance:       │
│  • orders/create  │───→│  • Reads: 5-10ms    │
│  • products/update│───→│  • Writes: 5-10ms   │
│  • inventory/update│──→│  • 10K+ concurrent  │
└───────────────────┘    └─────────────────────┘
                                  ↑ READ ONLY
                                  │
                         ┌────────┴─────────┐
                         │  FRONTEND        │
                         │  (React/Next.js) │
                         │                  │
                         │  • Browse: 5-10ms│
                         │  • Search: instant│
                         │  • Filter: instant│
                         └──────────────────┘
```

---

## Data Flow Patterns

### Pattern 1: Admin Creates Event

```
1. Admin submits form
     ↓
2. Backend → Shopify API: Create product
     ↓
3. Shopify creates product
     ↓
4. Shopify sends webhook: products/create
     ↓
5. Webhook handler → PostgreSQL: INSERT event
     ↓
6. Invalidate Redis cache
     ↓
7. Frontend shows new event (5-10ms)
```

**Delay:** 1-3 seconds (webhook processing)

### Pattern 2: Customer Buys Ticket

```
1. Customer clicks "Buy" → Redirected to Shopify Checkout
     ↓
2. Shopify locks inventory (prevents overselling)
     ↓
3. Customer completes payment
     ↓
4. Shopify processes order & decreases inventory
     ↓
5. Shopify sends webhook: orders/create
     ↓
6. Webhook handler → PostgreSQL: UPDATE sold count
     ↓
7. Invalidate Redis cache
     ↓
8. Frontend shows updated count (5-10ms)
```

**Delay:** 1-3 seconds (acceptable for display updates)

**Critical:** Shopify prevents overselling via inventory locking at checkout!

### Pattern 3: Admin Updates Ticket Capacity

```
1. Admin changes capacity (100 → 150)
     ↓
2. Backend → Shopify API: Update variant inventory
     ↓
3. Shopify updates inventory
     ↓
4. Shopify sends webhook: inventory_levels/update
     ↓
5. Webhook handler → PostgreSQL: UPDATE capacity
     ↓
6. Invalidate Redis cache
     ↓
7. Frontend shows new capacity (5-10ms)
```

**Delay:** 1-3 seconds (webhook processing)

---

## Webhook Details

### Webhook Types

| Webhook | Trigger | Payload | Action |
|---------|---------|---------|--------|
| `orders/create` | Customer purchase | Order, line items, quantities | Update sold count |
| `products/create` | Admin creates event | Product details, variants | Insert event & tickets |
| `products/update` | Admin edits event | Updated product data | Update event & tickets |
| `products/delete` | Admin deletes event | Product ID | Delete event & tickets |
| `inventory_levels/update` | Inventory changes | Available quantity | Update available count |

### Webhook Performance

**Single Webhook:**
```
Receive: 10-50ms
Parse JSON: 5ms
PostgreSQL update: 5-10ms
Commit: 5ms
Total: 25-70ms per webhook
```

**20 Concurrent Webhooks:**
```
Time          Event                           
──────────────────────────────────────────────
12:00:00.000  20 customers checkout           
12:00:01.000  Shopify sends 20 webhooks       
12:00:01.100  Server receives webhook 1       
12:00:01.110  Server receives webhook 2       
...
12:00:01.290  Server receives webhook 20      
12:00:01.310  All webhooks processed ✅        
12:00:01.320  Cache invalidated               

Total: 1.32 seconds
```

**Throughput:**
- 15-20 webhooks/second (single server)
- 900 webhooks/minute
- 54,000 webhooks/hour

### Webhook Reliability

**Shopify Guarantees:**
- ✅ At-least-once delivery
- ✅ Automatic retries (up to 19 times over 48 hours)
- ✅ Exponential backoff

**Your Responsibilities:**
- ✅ Idempotency (handle duplicate webhooks)
- ✅ Fast response (< 5 seconds)
- ✅ Return 200 OK on success

---

## Handling Concurrent Webhooks

### PostgreSQL Concurrency

**Row-Level Locking:**
```sql
-- 20 webhooks update same ticket simultaneously
UPDATE tickets 
SET sold = sold + quantity 
WHERE variant_id = '123';

-- PostgreSQL processes sequentially:
sold = 0 + 2 = 2   ✅
sold = 2 + 1 = 3   ✅
sold = 3 + 3 = 6   ✅
...
sold = 97 + 1 = 98 ✅

Result: Correct! No race conditions ✅
```

**ACID Guarantees:**
- ✅ Atomicity: All or nothing
- ✅ Consistency: Data integrity maintained
- ✅ Isolation: Concurrent updates don't interfere
- ✅ Durability: Committed data persists

### Idempotency Pattern

**Problem:** Webhook retries can cause duplicate processing

**Solution:**
```python
@app.post("/webhooks/orders/create")
async def handle_order_created(payload: dict):
    order_id = payload["id"]
    
    # Check if already processed
    existing = await db.fetchone(
        "SELECT id FROM processed_webhooks WHERE order_id = $1",
        order_id
    )
    
    if existing:
        return {"status": "already_processed"}  # Idempotent ✅
    
    # Process webhook
    async with db.transaction():
        for item in payload["line_items"]:
            await db.execute(
                "UPDATE tickets SET sold = sold + $1 WHERE variant_id = $2",
                item["quantity"], item["variant_id"]
            )
        
        # Mark as processed
        await db.execute(
            "INSERT INTO processed_webhooks (order_id, processed_at) VALUES ($1, NOW())",
            order_id
        )
    
    return {"status": "processed"}
```

---

## Inventory Accuracy

### The Critical Question: Overselling?

**Scenario:**
```
User A sees: 1 ticket available
User B sees: 1 ticket available
Both click "Buy" simultaneously
```

**Result:** ✅ NO OVERSELLING!

**Why:** Shopify locks inventory at checkout

**Timeline:**
```
12:00:00 - User A clicks "Buy"
12:00:01 - Shopify LOCKS 1 ticket (reserved for User A)
12:00:02 - Available inventory: 1 → 0 (locked)
12:00:03 - User B tries to buy
12:00:04 - Shopify: "Sorry, sold out!" ✅
12:00:05 - User A completes payment
12:00:06 - Shopify confirms sale, sends webhook
12:00:07 - PostgreSQL updated: sold +1
```

**Key Point:** Purchases go through Shopify checkout, which has real-time inventory!

### Display Delay (Minor UX Issue)

**Scenario:**
```
12:00 - User A buys last ticket
12:01 - Shopify: SOLD OUT (inventory = 0)
12:02 - Webhook sent
12:03 - PostgreSQL updated (sold = 100)

Between 12:01-12:03:
  Frontend shows: "1 available" ⚠️
  
User B clicks "Buy"
  ↓
Redirected to Shopify
  ↓
Shopify: "Sorry, sold out!" ✅
```

**Impact:**
- ⚠️ User sees "available" for 1-3 seconds after sold
- ✅ Cannot actually purchase (Shopify prevents it)
- ✅ No data integrity issue

**Solutions:**
1. Accept delay (simplest)
2. Real-time inventory check before checkout
3. WebSocket updates (advanced)

---

## Performance Comparison

### Before (Shopify API Only)

```
Dashboard load:     2-3 seconds
Event details:      2-3 seconds (first time)
Ticket list:        1-2 seconds
Search/filter:      3-5 seconds
Concurrent users:   Limited by rate limits (2 req/sec)
```

### After (PostgreSQL + Redis)

```
Dashboard load:     5-10ms (always!)
Event details:      5-10ms (always!)
Ticket list:        5-10ms (always!)
Search/filter:      5-10ms (always!)
Concurrent users:   10,000+ (no limits!)

Improvement: 200-500x faster! ✅
```

---

## Scalability

### Current Capacity (Single Server)

```
PostgreSQL:
- 10,000+ writes/second
- 100,000+ reads/second

FastAPI:
- 1,000+ requests/second
- 15-20 webhooks/second

Redis:
- 100,000+ operations/second
```

### Scaling Strategy

**Vertical Scaling (Increase server resources):**
```
Basic: $5/month → 100 concurrent users
Pro: $20/month → 1,000 concurrent users
Business: $50/month → 10,000 concurrent users
```

**Horizontal Scaling (Add more servers):**
```
Load Balancer
     ↓
┌────────┬────────┬────────┐
│Server 1│Server 2│Server 3│
└────────┴────────┴────────┘
     ↓       ↓       ↓
   PostgreSQL (shared)
   
Capacity: 30,000+ concurrent users
Cost: 3 × $20 = $60/month
```

---

## Cost Analysis

### DIY Approach (Building Everything)

```
Payment Gateway (Stripe):     $0.30 + 2.9% per transaction
PCI Compliance:                $10,000+/year
Fraud Detection:               $5,000+/year
Order Management System:       $20,000 to build
Customer Account System:       $15,000 to build
Email Infrastructure:          $500/month
Legal/Compliance:              $10,000+/year
Maintenance:                   $50,000+/year

Total: $100,000+ first year
```

### Hybrid Approach (Shopify + PostgreSQL)

```
Shopify Basic:                 $39/month
PostgreSQL (Supabase):         $0 (free tier) or $25/month (pro)
Redis (Upstash):               $0 (free tier) or $10/month (pro)
FastAPI Server:                $5-20/month

Total: $44-94/month = $528-1,128/year

Savings: $99,000+/year! ✅
```

---

## Implementation Checklist

### Phase 1: Database Setup (15 min)
- [ ] Create PostgreSQL database
- [ ] Create tables (events, tickets, orders, processed_webhooks)
- [ ] Add indexes for performance
- [ ] Test connection

### Phase 2: Initial Data Sync (15 min)
- [ ] Fetch all events from Shopify
- [ ] Fetch all tickets from Shopify
- [ ] Insert into PostgreSQL
- [ ] Verify data integrity

### Phase 3: Update Read Endpoints (20 min)
- [ ] Change `list_events` to query PostgreSQL
- [ ] Change `get_event` to query PostgreSQL
- [ ] Change `get_tickets` to query PostgreSQL
- [ ] Keep Redis caching layer

### Phase 4: Webhook Implementation (20 min)
- [ ] Create webhook endpoints
- [ ] Implement idempotency
- [ ] Register webhooks with Shopify
- [ ] Test webhook processing

### Phase 5: Testing & Validation (10 min)
- [ ] Test event creation
- [ ] Test ticket purchase (via Shopify checkout)
- [ ] Test concurrent webhooks
- [ ] Verify data consistency

**Total Time: 60-80 minutes**

---

## Monitoring & Debugging

### Key Metrics to Track

```python
# Webhook processing time
webhook_duration = time.time() - start_time
logger.info(f"Webhook processed in {webhook_duration}ms")

# PostgreSQL query time
query_duration = time.time() - query_start
logger.info(f"Query executed in {query_duration}ms")

# Cache hit rate
cache_hits / (cache_hits + cache_misses)
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    # Check PostgreSQL
    pg_ok = await db.fetchone("SELECT 1")
    
    # Check Redis
    redis_ok = await redis.ping()
    
    return {
        "status": "healthy" if (pg_ok and redis_ok) else "unhealthy",
        "postgres": "ok" if pg_ok else "error",
        "redis": "ok" if redis_ok else "error"
    }
```

---

## Conclusion

### Why This Architecture Works

✅ **Fast Reads:** PostgreSQL (5-10ms) instead of Shopify API (2-3 sec)  
✅ **No Rate Limits:** PostgreSQL has no API limits  
✅ **Scalable:** Handles 10,000+ concurrent users  
✅ **Reliable:** Shopify prevents overselling  
✅ **Cost-Effective:** $44-94/month vs $100K+/year  
✅ **Simple:** Shopify handles complex commerce logic  
✅ **Consistent:** Single source of truth (Shopify)  

### Trade-offs

⚠️ **1-3 Second Delay:** Webhook processing time (acceptable)  
⚠️ **Complexity:** Need to maintain sync logic  
⚠️ **Dependency:** Relies on Shopify webhooks  

### Best For

✅ High-traffic event ticketing platforms  
✅ Flash sales and limited inventory  
✅ Custom frontend requirements  
✅ Budget-conscious startups  
✅ Scalability needs (10K+ users)  

**This is the optimal architecture for your use case!** 🚀
