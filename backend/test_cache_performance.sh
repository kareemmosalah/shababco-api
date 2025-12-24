#!/bin/bash

echo "=========================================="
echo "TESTING REDIS CACHE PERFORMANCE"
echo "=========================================="
echo ""

API_URL="http://localhost:8000/api/v1/events"
TOKEN="YOUR_JWT_TOKEN"  # You'll need to replace this

echo "Step 1: Clear Redis cache"
echo "------------------------------------------"
redis-cli FLUSHDB
echo "✅ Cache cleared"
echo ""

echo "Step 2: First request (Cache MISS - should be slow)"
echo "------------------------------------------"
echo "Timing first request..."
time curl -s -w "\nTime: %{time_total}s\n" \
  -H "Authorization: Bearer $TOKEN" \
  "$API_URL?page=1&limit=20" > /dev/null
echo ""

echo "Step 3: Second request (Cache HIT - should be fast!)"
echo "------------------------------------------"
echo "Timing second request..."
time curl -s -w "\nTime: %{time_total}s\n" \
  -H "Authorization: Bearer $TOKEN" \
  "$API_URL?page=1&limit=20" > /dev/null
echo ""

echo "Step 4: Third request (Cache HIT - should be fast!)"
echo "------------------------------------------"
echo "Timing third request..."
time curl -s -w "\nTime: %{time_total}s\n" \
  -H "Authorization: Bearer $TOKEN" \
  "$API_URL?page=1&limit=20" > /dev/null
echo ""

echo "=========================================="
echo "Check Redis cache keys:"
redis-cli KEYS "events:*"
echo "=========================================="
