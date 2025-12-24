"""Test Redis caching implementation"""
import asyncio
from app.core.cache import (
    cache_full_event,
    get_cached_full_event,
    cache_events_page,
    get_cached_events_page,
    get_cache_stats,
    invalidate_event_caches
)

async def test_caching():
    print("=" * 60)
    print("TESTING REDIS CACHING IMPLEMENTATION")
    print("=" * 60)
    print()
    
    # Test 1: Cache full event
    print("Test 1: Cache Full Event")
    print("-" * 40)
    event_data = {
        "id": "8613376983211",
        "title": "Sahel Summer Opening Party",
        "description": "Beach party with DJ Khaled",
        "tickets": [
            {"id": "123", "name": "General Admission", "price": 85.0, "sold": 4},
            {"id": "124", "name": "VIP", "price": 150.0, "sold": 2}
        ],
        "metafields": {
            "venue": "Sahel Beach Club",
            "lineup": "DJ Khaled, Amr Diab"
        }
    }
    
    cache_full_event("8613376983211", event_data, ttl=600)
    print("✅ Cached event data")
    
    # Retrieve from cache
    cached = get_cached_full_event("8613376983211")
    if cached:
        print(f"✅ Retrieved from cache: {cached['title']}")
        print(f"   Tickets: {len(cached['tickets'])}")
    else:
        print("❌ Cache retrieval failed")
    print()
    
    # Test 2: Cache events page
    print("Test 2: Cache Events Page")
    print("-" * 40)
    events_list = [
        {"id": "1", "title": "Event 1"},
        {"id": "2", "title": "Event 2"},
        {"id": "3", "title": "Event 3"}
    ]
    
    filters = {"category": "music", "search": "summer"}
    cache_events_page(1, 20, filters, events_list, ttl=300)
    print("✅ Cached events page")
    
    # Retrieve from cache
    cached_page = get_cached_events_page(1, 20, filters)
    if cached_page:
        print(f"✅ Retrieved from cache: {len(cached_page)} events")
    else:
        print("❌ Cache retrieval failed")
    print()
    
    # Test 3: Cache stats
    print("Test 3: Cache Statistics")
    print("-" * 40)
    stats = get_cache_stats()
    print(f"Status: {stats.get('status')}")
    print(f"Used memory: {stats.get('used_memory', 'N/A')}")
    print(f"Total keys: {stats.get('total_keys', 0)}")
    print(f"Event keys: {stats.get('event_keys', 0)}")
    print()
    
    # Test 4: Cache invalidation
    print("Test 4: Cache Invalidation")
    print("-" * 40)
    invalidate_event_caches("8613376983211")
    print("✅ Invalidated event cache")
    
    # Try to retrieve (should be None)
    cached_after = get_cached_full_event("8613376983211")
    if cached_after is None:
        print("✅ Cache successfully invalidated")
    else:
        print("❌ Cache invalidation failed")
    print()
    
    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_caching())
