# Quick test to see event fields
import asyncio
from app.integrations.shopify.products import list_products

async def test():
    result = await list_products(limit=1, query="product_type:event")
    if result["products"]:
        event = result["products"][0]
        print("Event fields:")
        for key in event.keys():
            print(f"  - {key}: {event[key][:50] if isinstance(event[key], str) else event[key]}")

asyncio.run(test())
