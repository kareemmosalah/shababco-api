"""
Migration script to set is_featured=false for all existing events.
Run this once before deploying the featured events feature.

Usage:
    cd backend
    uv run python scripts/set_featured_false.py
"""
import asyncio
import logging
from app.integrations.shopify.products import list_products
from app.integrations.shopify.featured import update_is_featured

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_featured_field():
    """Set is_featured=false for all existing events."""
    logger.info("🚀 Starting migration: Setting is_featured=false for all events")
    
    # Fetch all events
    all_events = []
    cursor = None
    
    while True:
        result = await list_products(limit=50, query="product_type:event", cursor=cursor)
        events = result["products"]
        all_events.extend(events)
        
        if not result.get("has_next_page", False):
            break
        
        cursor = result.get("end_cursor")
    
    logger.info(f"📊 Found {len(all_events)} events to update")
    
    # Update each event
    success_count = 0
    error_count = 0
    
    for event in all_events:
        product_id = event.get("shopify_product_id")
        title = event.get("title", "Unknown")
        
        try:
            # Check if already has is_featured field
            current_featured = event.get("is_featured")
            
            if current_featured is None:
                # Set to false if not set
                await update_is_featured(product_id, False)
                logger.info(f"✅ Updated: {title} (ID: {product_id})")
                success_count += 1
            else:
                logger.info(f"⏭️  Skipped: {title} (ID: {product_id}) - already has is_featured={current_featured}")
        
        except Exception as e:
            logger.error(f"❌ Failed to update {title} (ID: {product_id}): {str(e)}")
            error_count += 1
    
    logger.info(f"\n📈 Migration complete!")
    logger.info(f"   ✅ Success: {success_count}")
    logger.info(f"   ⏭️  Skipped: {len(all_events) - success_count - error_count}")
    logger.info(f"   ❌ Errors: {error_count}")


if __name__ == "__main__":
    asyncio.run(migrate_featured_field())
