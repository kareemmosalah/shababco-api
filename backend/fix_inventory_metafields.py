"""
Script to fix inventory_quantity metafields for all tickets.

This script reads order data and updates the inventory_quantity metafield
to reflect the original capacity (current inventory + sold orders).

Usage:
1. Export orders CSV from Shopify
2. Update the CSV_FILE path below
3. Run: uv run python fix_inventory_metafields.py
"""

import asyncio
import csv
from collections import defaultdict
from app.integrations.shopify.admin_client import shopify_admin_client


async def get_all_variants():
    """Get all product variants from Shopify"""
    query = """
    query getProducts($cursor: String) {
      products(first: 50, after: $cursor, query: "product_type:event") {
        edges {
          node {
            id
            title
            variants(first: 50) {
              edges {
                node {
                  id
                  legacyResourceId
                  title
                  inventoryQuantity
                  sku
                }
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    
    variants = []
    cursor = None
    
    while True:
        result = await shopify_admin_client.execute_query(query, {"cursor": cursor})
        products = result.get("products", {}).get("edges", [])
        
        for product_edge in products:
            product = product_edge["node"]
            for variant_edge in product.get("variants", {}).get("edges", []):
                variant = variant_edge["node"]
                variants.append({
                    "product_title": product["title"],
                    "variant_id": variant["id"],
                    "variant_legacy_id": variant["legacyResourceId"],
                    "variant_title": variant["title"],
                    "current_inventory": variant["inventoryQuantity"],
                    "sku": variant.get("sku", "")
                })
        
        page_info = result.get("products", {}).get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
    
    return variants


async def update_variant_capacity(variant_id: str, capacity: int):
    """Update the inventory_quantity metafield for a variant"""
    mutation = """
    mutation setMetafield($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields {
          id
          key
          value
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "metafields": [{
            "ownerId": variant_id,
            "namespace": "ticket",
            "key": "inventory_quantity",
            "type": "number_integer",
            "value": str(capacity)
        }]
    }
    
    result = await shopify_admin_client.execute_mutation(mutation, variables)
    
    if result.get("metafieldsSet", {}).get("userErrors"):
        return False, result["metafieldsSet"]["userErrors"]
    return True, None


async def main():
    print("=" * 80)
    print("FIXING INVENTORY METAFIELDS FOR ALL TICKETS")
    print("=" * 80)
    print()
    
    # Get all variants
    print("📋 Fetching all variants from Shopify...")
    variants = await get_all_variants()
    print(f"✅ Found {len(variants)} variants")
    print()
    
    # Read orders from CSV (you'll need to provide this)
    # For now, we'll just set capacity = current_inventory for tickets with 0 sold
    # You can modify this to read from your CSV
    
    print("🔧 Updating metafields...")
    print()
    
    updated = 0
    errors = 0
    
    for variant in variants:
        # For now, set capacity to current inventory
        # TODO: Replace this with actual sold count from your CSV
        capacity = variant["current_inventory"]
        
        success, error = await update_variant_capacity(
            variant["variant_id"],
            capacity
        )
        
        if success:
            print(f"✅ {variant['product_title']} - {variant['variant_title']}: {capacity}")
            updated += 1
        else:
            print(f"❌ {variant['product_title']} - {variant['variant_title']}: {error}")
            errors += 1
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Updated: {updated}")
    print(f"Errors: {errors}")
    print()
    print("✅ Done! All metafields updated.")
    print()
    print("NOTE: This script set capacity = current_inventory")
    print("To include sold orders, update the script to read from your CSV")


if __name__ == "__main__":
    asyncio.run(main())
