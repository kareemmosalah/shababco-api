#!/bin/bash

echo "=========================================="
echo "CACHE VALIDATION TEST"
echo "=========================================="
echo ""
echo "Cache has been cleared. Now testing..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Step 1: Check Redis is empty"
echo "------------------------------------------"
KEYS=$(redis-cli DBSIZE)
echo "Redis keys: $KEYS"
if [ "$KEYS" = "(integer) 0" ]; then
    echo -e "${GREEN}✅ Cache is empty (cold start)${NC}"
else
    echo -e "${YELLOW}⚠️ Cache has $KEYS keys${NC}"
fi
echo ""

echo "Step 2: Monitor what happens when you:"
echo "------------------------------------------"
echo "1. Open dashboard (http://localhost:5173/dashboard)"
echo "   → Should take 2-3 seconds (fetching from Shopify)"
echo "   → Watch backend logs for: '⚠️ Cache MISS'"
echo ""
echo "2. Click on an event"
echo "   → Should be INSTANT (50ms)"
echo "   → Watch backend logs for: '✅ Cache HIT'"
echo ""
echo "3. View tickets"
echo "   → Should be INSTANT (50ms)"
echo "   → Watch backend logs for: '✅ Cache HIT'"
echo ""

echo "Press ENTER when you've opened the dashboard..."
read

echo ""
echo "Step 3: Check what got cached"
echo "------------------------------------------"
echo "Events cached:"
redis-cli KEYS "events:*" | wc -l | xargs echo "  Count:"
redis-cli KEYS "events:*" | head -5
echo ""
echo "Tickets cached:"
redis-cli KEYS "tickets:*" | wc -l | xargs echo "  Count:"
redis-cli KEYS "tickets:*" | head -5
echo ""

echo "Step 4: Check cache size"
echo "------------------------------------------"
redis-cli INFO memory | grep used_memory_human
echo ""

echo "=========================================="
echo "VALIDATION COMPLETE!"
echo "=========================================="
echo ""
echo "Expected behavior:"
echo "✅ Dashboard first load: 2-3 sec (Cache MISS)"
echo "✅ Event page: Instant (Cache HIT)"
echo "✅ Tickets: Instant (Cache HIT)"
echo "✅ Dashboard second load: Instant (Cache HIT)"
