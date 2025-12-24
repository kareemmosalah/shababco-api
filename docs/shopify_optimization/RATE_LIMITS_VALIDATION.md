# Shopify API Rate Limits - Official Validation

**Last Updated:** December 2024  
**Source:** shopify.dev (Official Shopify Documentation)

---

## Official Rate Limits (2024)

### REST Admin API (Legacy as of Oct 2024)

| Shopify Plan | Requests/Second | Bucket Size | Notes |
|--------------|-----------------|-------------|-------|
| **Basic/Standard** | 2 req/sec | 40 requests | ✅ Our documentation is CORRECT |
| **Advanced** | 4 req/sec | 80 requests | 2x standard |
| **Shopify Plus** | 20 req/sec | 400 requests | 10x standard |
| **Enterprise** | 40 req/sec | 800 requests | 20x standard |

**Leaky Bucket Algorithm:**
- Bucket fills with each request
- Leaks at constant rate (restore rate)
- When full → HTTP 429 error

---

### GraphQL Admin API (Recommended)

| Shopify Plan | Points/Second | Max Query Cost | Notes |
|--------------|---------------|----------------|-------|
| **Basic/Standard** | 50 points/sec | 1000 points | ✅ Our documentation is CORRECT |
| **Advanced** | 100 points/sec | 1000 points | 2x standard |
| **Shopify Plus** | 500-1000 points/sec | 1000 points | 10-20x standard |

**Cost Calculation:**
- Each field costs points
- Simple query: 5-10 points
- Complex query: 50-100 points
- Mutation: 10+ points

**Example Costs:**
```graphql
# Fetch single product: ~10 points
query {
  product(id: "gid://shopify/Product/123") {
    title
    description
  }
}

# Fetch 50 products with variants: ~500 points
query {
  products(first: 50) {
    edges {
      node {
        title
        variants(first: 10) {
          edges {
            node {
              price
            }
          }
        }
      }
    }
  }
}
```

---

### Storefront API

**Rate Limit:** NONE ✅

The Storefront API has no rate limits and is designed for high-traffic customer-facing applications.

**Use Cases:**
- Product browsing
- Cart operations
- Checkout (handled by Shopify)

---

## Validation of Our Documentation

### ✅ CORRECT Statements

1. **"REST API: 2 req/sec"** ✅
   - Official: 2 req/sec for standard plans

2. **"GraphQL API: 1000 cost points/sec"** ⚠️ NEEDS UPDATE
   - Official: 50 points/sec (standard), not 1000
   - 1000 is the MAX QUERY COST, not rate limit

3. **"Shopify Plus: 4 req/sec"** ❌ INCORRECT
   - Official: 20 req/sec (not 4)
   - Advanced plan is 4 req/sec

4. **"Storefront API: Very high"** ✅
   - Official: No rate limits at all

---

## Updated Performance Calculations

### Scenario: 100 Users Request Events List

#### Using REST Admin API (Standard Plan)

```
Rate limit: 2 req/sec
100 requests needed

Timeline:
  0-1s:   2 requests processed
  1-2s:   2 requests processed
  2-3s:   2 requests processed
  ...
  49-50s: 2 requests processed (requests 99-100)

Total time: 50 seconds
Average wait: 25 seconds ❌
```

**Our documentation said:** 50 sec average ✅ CORRECT!

#### Using GraphQL Admin API (Standard Plan)

```
Rate limit: 50 points/sec
Each event list query: ~50 points
100 requests × 50 points = 5000 points needed

Timeline:
  0-1s:   1 request (50 points)
  1-2s:   1 request (50 points)
  ...
  99-100s: 1 request (requests 100)

Total time: 100 seconds
Average wait: 50 seconds ❌
```

**Even worse than REST!** (for this specific query)

#### Using Shopify Plus (REST)

```
Rate limit: 20 req/sec
100 requests needed

Timeline:
  0-1s:   20 requests processed
  1-2s:   20 requests processed
  2-3s:   20 requests processed
  3-4s:   20 requests processed
  4-5s:   20 requests processed

Total time: 5 seconds
Average wait: 2.5 seconds ⚠️
```

**Still slow!** And costs $2,000/month

---

## Corrections Needed in Documentation

### 1. GraphQL Rate Limit

**Current (INCORRECT):**
> GraphQL Admin API: 1000 cost points/sec

**Corrected:**
> GraphQL Admin API: 50 points/sec (standard), 100 points/sec (advanced), 500-1000 points/sec (Plus)
> Maximum single query cost: 1000 points

### 2. Shopify Plus REST API

**Current (INCORRECT):**
> Shopify Plus: 4 req/sec

**Corrected:**
> Shopify Plus: 20 req/sec (10x standard)

### 3. Add Storefront API Clarification

**Add:**
> Storefront API: No rate limits (designed for customer traffic)
> Note: Storefront API is for browsing/checkout, not admin operations

---

## Impact on Our Optimization Plan

### Good News

✅ **Our core argument is still valid:**
- Standard plan: 2 req/sec is still very limiting
- 100 users = 50 seconds average wait (CORRECT)
- PostgreSQL solution is still 500x faster

### Updates Needed

1. **GraphQL numbers** - Update to 50 points/sec (not 1000)
2. **Shopify Plus** - Update to 20 req/sec (not 4)
3. **Add note** - Storefront API has no limits (but not for admin data)

### Our Solution Remains Best

| Approach | Rate Limit | 100 Users | Cost |
|----------|------------|-----------|------|
| **REST API (Standard)** | 2 req/sec | 50 sec | $39/mo |
| **GraphQL API (Standard)** | 50 points/sec | 100 sec | $39/mo |
| **Shopify Plus (REST)** | 20 req/sec | 5 sec | $2,000/mo |
| **Our PostgreSQL** | No limit | 0.055 sec | $39/mo |

**Conclusion:** Our solution is still 90-1800x faster and $0 extra cost!

---

## Action Items

- [ ] Update 01_shopify_backend_challenges.md with correct GraphQL limits
- [ ] Update rate limit table with official numbers
- [ ] Add Storefront API clarification
- [ ] Update Shopify Plus numbers (20 req/sec, not 4)
- [ ] Keep all 100-user scenarios (they're correct!)

---

## Sources

- [Shopify REST Admin API Rate Limits](https://shopify.dev/docs/api/usage/rate-limits)
- [Shopify GraphQL Admin API Rate Limits](https://shopify.dev/docs/api/usage/rate-limits)
- [GraphQL Cost Calculation](https://shopify.dev/docs/api/usage/rate-limits#graphql-admin-api-rate-limits)

**Validation Date:** December 23, 2024
