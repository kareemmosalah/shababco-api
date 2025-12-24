"""
Fix capacity metafields for Sahel Summer Opening Party tickets
Based on actual orders: 4 General Admission, 1 Regular
"""

import asyncio
from app.integrations.shopify.admin_client import shopify_admin_client


# Sahel Summer Opening Party ticket data
TICKETS_TO_FIX = {
    "45970052972715": {  # General Admission
        "name": "General Admission",
        "sold": 4,
        "current_inventory": None  # Will fetch from Shopify
    },
    "45970217992363": {  # Regular
        "name": "Regular", 
        "sold": 1,
        "current_inventory": None
    },
    "45970219499691": {  # VIP
        "name": "VIP",
        "sold": 0,
        "current_inventory": None
    },
    "45970257739947": {  # Student
        "name": "Student",
        "sold": 0,
        "current_inventory": None
    }
}


async def get_current_inventory(variant_id: str):
    """Get current inventory from Shopify"""
    query = """
    query getVariant($id: ID!) {
      productVariant(id: $id) {
        inventoryQuantity
      }
    }
    """
    
    graphql_id = f"gid://shopify/ProductVariant/{variant_id}"
    result = await shopify_admin_client.execute_query(query, {"id": graphql_id})
    return result.get("productVariant", {}).get("inventoryQuantity", 0)


async def update_capacity_metafield(variant_id: str, capacity: int):
    """Update inventory_quantity metafield"""
    graphql_id = f"gid://shopify/ProductVariant/{variant_id}"
    
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
            "ownerId": graphql_id,
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
    print("FIXING SAHEL SUMMER OPENING PARTY TICKET CAPACITIES")
    print("=" * 80)
    print()
    print("Based on actual orders:")
    print("  - General Admission: 4 sold")
    print("  - Regular: 1 sold")
    print("  - VIP: 0 sold")
    print("  - Student: 0 sold")
    print()
    
    # Fetch current inventory for all tickets
    print("📋 Fetching current inventory from Shopify...")
    for variant_id, data in TICKETS_TO_FIX.items():
        current_inv = await get_current_inventory(variant_id)
        data["current_inventory"] = current_inv
        print(f"  {data['name']}: {current_inv} available")
    print()
    
    # Calculate and update capacities
    print("🔧 Updating capacity metafields...")
    print()
    
    for variant_id, data in TICKETS_TO_FIX.items():
        # Original capacity = current inventory + sold orders
        original_capacity = data["current_inventory"] + data["sold"]
        
        success, error = await update_capacity_metafield(variant_id, original_capacity)
        
        if success:
            print(f"✅ {data['name']}:")
            print(f"   Current inventory: {data['current_inventory']}")
            print(f"   Sold: {data['sold']}")
            print(f"   Original capacity: {original_capacity}")
        else:
            print(f"❌ {data['name']}: {error}")
        print()
    
    print("=" * 80)
    print("✅ DONE! All metafields updated.")
    print("=" * 80)
    print()
    print("Now the sold counts will be accurate:")
    print(f"  - General Admission: {TICKETS_TO_FIX['45970052972715']['sold']} sold")
    print(f"  - Regular: {TICKETS_TO_FIX['45970217992363']['sold']} sold")
    print(f"  - VIP: {TICKETS_TO_FIX['45970219499691']['sold']} sold")
    print(f"  - Student: {TICKETS_TO_FIX['45970257739947']['sold']} sold")


if __name__ == "__main__":
    asyncio.run(main())
