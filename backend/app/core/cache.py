"""
Enhanced Redis cache for full event schema caching.

Caches complete event data including:
- Event metadata (title, description, dates, etc.)
- All tickets with pricing and availability
- Metafields (venue, lineup, custom fields)
- Images and media

Storage per event: ~15 KB
Capacity: 1000+ events in free tier (256 MB)
"""

import redis
import json
import hashlib
from typing import Optional, Any, Dict, List
from functools import wraps
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize Redis client
try:
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test connection
    redis_client.ping()
    logger.info(f"✅ Redis connected: {REDIS_URL}")
    REDIS_AVAILABLE = True
except Exception as e:
    logger.warning(f"⚠️ Redis not available: {e}. Caching disabled.")
    redis_client = None
    REDIS_AVAILABLE = False


def generate_cache_key(*args, **kwargs) -> str:
    """Generate a unique cache key from arguments"""
    key_data = f"{args}:{sorted(kwargs.items())}"
    return hashlib.md5(key_data.encode()).hexdigest()


def cache_get(key: str) -> Optional[Any]:
    """Get data from cache"""
    if not REDIS_AVAILABLE:
        return None
    
    try:
        data = redis_client.get(key)
        if data:
            logger.debug(f"✅ Cache HIT: {key}")
            return json.loads(data)
        logger.debug(f"⚠️ Cache MISS: {key}")
        return None
    except Exception as e:
        logger.error(f"❌ Cache GET error: {e}")
        return None


def cache_set(key: str, value: Any, ttl: int = 300):
    """
    Cache data with TTL (Time To Live)
    
    Args:
        key: Cache key
        value: Data to cache (must be JSON serializable)
        ttl: Time to live in seconds (default: 5 minutes)
    """
    if not REDIS_AVAILABLE:
        return
    
    try:
        redis_client.setex(
            key,
            ttl,
            json.dumps(value, default=str)  # default=str handles datetime, Decimal, etc.
        )
        logger.debug(f"💾 Cache SET: {key} (TTL: {ttl}s)")
    except Exception as e:
        logger.error(f"❌ Cache SET error: {e}")


def cache_delete(pattern: str):
    """
    Delete cache keys matching pattern
    
    Args:
        pattern: Redis key pattern (e.g., "events:*")
    """
    if not REDIS_AVAILABLE:
        return
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.info(f"🗑️ Cache INVALIDATED: {len(keys)} keys matching '{pattern}'")
    except Exception as e:
        logger.error(f"❌ Cache DELETE error: {e}")


def cache_invalidate_all():
    """Invalidate all caches (use sparingly!)"""
    if not REDIS_AVAILABLE:
        return
    
    try:
        redis_client.flushdb()
        logger.warning("🗑️ Cache FLUSHED: All keys deleted")
    except Exception as e:
        logger.error(f"❌ Cache FLUSH error: {e}")


# ============================================================================
# FULL EVENT SCHEMA CACHING
# ============================================================================

def cache_full_event(event_id: str, event_data: Dict, ttl: int = 600):
    """
    Cache complete event with all tickets and metafields.
    
    Args:
        event_id: Shopify product ID
        event_data: Complete event object including tickets
        ttl: Cache duration (default: 10 minutes)
    
    Storage: ~15 KB per event
    """
    cache_key = f"events:full:{event_id}"
    cache_set(cache_key, event_data, ttl=ttl)
    logger.info(f"💾 Cached full event: {event_id} ({ttl}s TTL)")


def get_cached_full_event(event_id: str) -> Optional[Dict]:
    """Get complete cached event data"""
    cache_key = f"events:full:{event_id}"
    return cache_get(cache_key)


def cache_events_page(page: int, limit: int, filters: Dict, events_data: List[Dict], ttl: int = 300):
    """
    Cache paginated events list.
    
    Args:
        page: Page number
        limit: Items per page
        filters: Filter parameters (category, search, etc.)
        events_data: List of events
        ttl: Cache duration (default: 5 minutes)
    """
    # Create cache key from parameters
    filter_str = json.dumps(filters, sort_keys=True) if filters else "none"
    cache_key = f"events:list:page={page}:limit={limit}:filters={hashlib.md5(filter_str.encode()).hexdigest()}"
    cache_set(cache_key, events_data, ttl=ttl)
    logger.info(f"💾 Cached events page: {page} ({len(events_data)} events, {ttl}s TTL)")


def get_cached_events_page(page: int, limit: int, filters: Dict) -> Optional[List[Dict]]:
    """Get cached events page"""
    filter_str = json.dumps(filters, sort_keys=True) if filters else "none"
    cache_key = f"events:list:page={page}:limit={limit}:filters={hashlib.md5(filter_str.encode()).hexdigest()}"
    return cache_get(cache_key)


def cache_event_tickets(event_id: str, tickets_data: List[Dict], ttl: int = 600):
    """
    Cache all tickets for an event.
    
    Args:
        event_id: Shopify product ID
        tickets_data: List of tickets with full data
        ttl: Cache duration (default: 10 minutes)
    """
    cache_key = f"tickets:event:{event_id}"
    cache_set(cache_key, tickets_data, ttl=ttl)
    logger.info(f"💾 Cached {len(tickets_data)} tickets for event: {event_id}")


def get_cached_event_tickets(event_id: str) -> Optional[List[Dict]]:
    """Get cached tickets for an event"""
    cache_key = f"tickets:event:{event_id}"
    return cache_get(cache_key)


# ============================================================================
# CACHE INVALIDATION STRATEGIES
# ============================================================================

def invalidate_event_caches(event_id: Optional[str] = None):
    """
    Invalidate event-related caches.
    
    Args:
        event_id: If provided, only invalidate caches for this event.
                  Otherwise, invalidate all event caches.
    """
    if event_id:
        # Invalidate specific event
        cache_delete(f"events:full:{event_id}")
        cache_delete(f"tickets:event:{event_id}")
        logger.info(f"🗑️ Invalidated caches for event: {event_id}")
    else:
        # Invalidate all events
        cache_delete("events:*")
        cache_delete("tickets:*")
        logger.warning("🗑️ Invalidated ALL event caches")


def invalidate_ticket_caches(ticket_id: Optional[str] = None, event_id: Optional[str] = None):
    """
    Invalidate ticket-related caches.
    
    Args:
        ticket_id: Ticket variant ID
        event_id: Parent event ID (more efficient than ticket_id)
    """
    if event_id:
        # Invalidate event's tickets cache
        cache_delete(f"tickets:event:{event_id}")
        cache_delete(f"events:full:{event_id}")
        logger.info(f"🗑️ Invalidated ticket caches for event: {event_id}")
    elif ticket_id:
        # Invalidate all ticket caches (less efficient)
        cache_delete("tickets:*")
        logger.warning(f"🗑️ Invalidated ALL ticket caches (ticket: {ticket_id})")


def invalidate_list_caches():
    """Invalidate all list/pagination caches"""
    cache_delete("events:list:*")
    logger.info("🗑️ Invalidated all list caches")


# ============================================================================
# CACHE STATISTICS
# ============================================================================

def get_cache_stats() -> Dict:
    """Get Redis cache statistics"""
    if not REDIS_AVAILABLE:
        return {"status": "unavailable"}
    
    try:
        info = redis_client.info("memory")
        stats = {
            "status": "connected",
            "used_memory": info.get("used_memory_human", "N/A"),
            "peak_memory": info.get("used_memory_peak_human", "N/A"),
            "total_keys": redis_client.dbsize(),
            "event_keys": len(redis_client.keys("events:*")),
            "ticket_keys": len(redis_client.keys("tickets:*")),
        }
        return stats
    except Exception as e:
        logger.error(f"❌ Error getting cache stats: {e}")
        return {"status": "error", "error": str(e)}


# Cache key patterns for easy reference
CACHE_PATTERNS = {
    "event_full": "events:full:{event_id}",
    "events_list": "events:list:*",
    "event_tickets": "tickets:event:{event_id}",
    "all_events": "events:*",
    "all_tickets": "tickets:*",
}
