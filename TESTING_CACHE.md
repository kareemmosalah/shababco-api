# How to Test Redis Caching

## Quick Test (Manual)

### Step 1: Check if Redis is Running
```bash
redis-cli ping
# Should return: PONG
```

### Step 2: Clear Cache (to see the difference)
```bash
redis-cli FLUSHDB
# Returns: OK
```

### Step 3: Open Your Frontend

**First Load (Cache MISS):**
1. Open browser DevTools (F12)
2. Go to Network tab
3. Navigate to Events page
4. Look at the API request time
5. **Should take:** 2-3 seconds ⚠️

**Second Load (Cache HIT):**
1. Refresh the page (F5)
2. Look at the API request time again
3. **Should take:** 50-100ms ✅ (20-30x faster!)

### Step 4: Check Cache Keys
```bash
redis-cli KEYS "events:*"
# Should show cached event keys
```

### Step 5: Monitor Cache in Real-Time
```bash
redis-cli MONITOR
# Shows all Redis operations in real-time
# Then refresh your frontend page
```

---

## Why You Might Not Feel a Difference

### Possible Reasons:

1. **Cache Already Warm**
   - If you've been testing, cache might already be populated
   - Solution: Run `redis-cli FLUSHDB` first

2. **Network is Fast**
   - If your internet is very fast, Shopify API might respond quickly
   - Difference is more noticeable on slower connections

3. **Small Dataset**
   - If you only have 1-2 events, difference is minimal
   - With 20+ events, difference is more noticeable

4. **Frontend Caching**
   - Browser might be caching responses
   - Solution: Hard refresh (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)

---

## Better Test: Use curl with Timing

### Test Script
```bash
#!/bin/bash

# Replace with your actual token
TOKEN="your_jwt_token_here"
API_URL="http://localhost:8000/api/v1/events?page=1&limit=20"

echo "Clearing cache..."
redis-cli FLUSHDB

echo ""
echo "Test 1: First request (Cache MISS)"
time curl -s -H "Authorization: Bearer $TOKEN" "$API_URL" > /dev/null

echo ""
echo "Test 2: Second request (Cache HIT)"
time curl -s -H "Authorization: Bearer $TOKEN" "$API_URL" > /dev/null

echo ""
echo "Test 3: Third request (Cache HIT)"
time curl -s -H "Authorization: Bearer $TOKEN" "$API_URL" > /dev/null
```

**Expected Results:**
- First request: ~2-3 seconds
- Second request: ~0.05 seconds (50ms)
- Third request: ~0.05 seconds (50ms)

---

## Check Backend Logs

Your FastAPI logs should show:
```
⚠️ Cache MISS for event list - fetching from Shopify
💾 Cached events page: 1 (20 events, 300s TTL)
✅ Cache HIT for event list
✅ Cache HIT for event list
```

---

## Current Limitation

**Remember:** Redis only helps AFTER the first request!

- **First user:** Still waits 2-3 seconds
- **Next users:** Get instant response (50ms)

**To fix this:** We need PostgreSQL (next step!)
