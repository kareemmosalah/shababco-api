"""
Enhanced caching for admin event management.
Caches full event data including tickets and metafields.
"""

from app.core.cache import cache_get, cache_set, cache_delete

# Cache full event details (event + tickets + metafields)
def cache_full_event(event_id: str, event_data: dict, ttl: int = 600):
    """
    Cache complete event data including tickets.
    
    Args:
        event_id: Shopify product ID
        event_data: Complete event object with tickets
        ttl: Cache duration in seconds (default: 10 minutes)
    """
    cache_key = f"events:full:{event_id}"
    cache_set(cache_key, event_data, ttl=ttl)


def get_cached_full_event(event_id: str):
    """Get cached full event data"""
    cache_key = f"events:full:{event_id}"
    return cache_get(cache_key)


def cache_admin_events_page(page: int, events_data: list, ttl: int = 600):
    """
    Cache admin events list page (20 events with full data).
    
    Args:
        page: Page number
        events_data: List of events with tickets
        ttl: Cache duration (default: 10 minutes)
    """
    cache_key = f"events:admin:page={page}"
    cache_set(cache_key, events_data, ttl=ttl)


def get_cached_admin_events_page(page: int):
    """Get cached admin events page"""
    cache_key = f"events:admin:page={page}"
    return cache_get(cache_key)


# Storage calculation helper
def estimate_cache_size(num_events: int) -> dict:
    """
    Estimate Redis storage needed.
    
    Returns:
        dict with storage estimates
    """
    kb_per_event = 15  # Event + 4 tickets + metafields
    
    return {
        "events": num_events,
        "size_kb": num_events * kb_per_event,
        "size_mb": (num_events * kb_per_event) / 1024,
        "redis_free_tier": "256 MB (Upstash)",
        "can_cache": (num_events * kb_per_event) / 1024 < 256
    }
