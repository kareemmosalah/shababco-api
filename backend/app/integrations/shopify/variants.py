"""
Shopify variant operations for ticket management.
Variants represent ticket types with pricing and inventory.
"""
import json
from typing import Dict, Any, Optional
from app.integrations.shopify.admin_client import shopify_admin_client


# GraphQL mutation to create product variants (bulk API)
CREATE_VARIANT_MUTATION = """
mutation createVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkCreate(productId: $productId, variants: $variants) {
    productVariants {
      id
      legacyResourceId
      title
      price
      compareAtPrice
      inventoryQuantity
      inventoryItem {
        id
      }
      metafields(first: 10, namespace: "ticket") {
        edges {
          node {
            key
            value
            type
          }
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

# GraphQL query to get shop's default location
GET_LOCATIONS_QUERY = """
query {
  locations(first: 1) {
    edges {
      node {
        id
        name
      }
    }
  }
}
"""

# GraphQL mutation to activate inventory tracking and set initial quantity
ACTIVATE_INVENTORY_MUTATION = """
mutation activateInventory($inventoryItemId: ID!, $locationId: ID!) {
  inventoryActivate(inventoryItemId: $inventoryItemId, locationId: $locationId) {
    inventoryLevel {
      id
      available
    }
    userErrors {
      field
      message
    }
  }
}
"""

# GraphQL mutation to adjust inventory quantity
ADJUST_INVENTORY_MUTATION = """
mutation adjustInventory($inventoryLevelId: ID!, $delta: Int!) {
  inventoryAdjustQuantity(input: {
    inventoryLevelId: $inventoryLevelId,
    availableDelta: $delta
  }) {
    inventoryLevel {
      available
    }
    userErrors {
      field
      message
    }
  }
}
"""


def _build_variant_metafields(ticket_data: Dict[str, Any]) -> list[Dict[str, Any]]:
    """
    Build metafields array for ticket variant.
    
    Args:
        ticket_data: Ticket data dictionary
        
    Returns:
        List of metafield objects
    """
    metafields = []
    
    # Description
    if ticket_data.get("description"):
        metafields.append({
            "namespace": "ticket",
            "key": "description",
            "type": "multi_line_text_field",
            "value": ticket_data["description"]
        })
    
    # Features (JSON array)
    if ticket_data.get("features"):
        metafields.append({
            "namespace": "ticket",
            "key": "features",
            "type": "json",
            "value": json.dumps(ticket_data["features"])
        })
    
    # Visibility
    metafields.append({
        "namespace": "ticket",
        "key": "is_visible",
        "type": "boolean",
        "value": str(ticket_data.get("is_visible", True)).lower()
    })
    
    # Max per order
    metafields.append({
        "namespace": "ticket",
        "key": "max_per_order",
        "type": "number_integer",
        "value": str(ticket_data.get("max_per_order", 10))
    })
    
    # Initial inventory quantity (for capacity tracking)
    metafields.append({
        "namespace": "ticket",
        "key": "inventory_quantity",
        "type": "number_integer",
        "value": str(ticket_data.get("inventory_quantity", 0))
    })
    
    # Ticket type
    metafields.append({
        "namespace": "ticket",
        "key": "ticket_type",
        "type": "single_line_text_field",
        "value": ticket_data["ticket_type"]
    })
    
    return metafields


async def get_default_location() -> str:
    """
    Get the shop's default location ID.
    
    Returns:
        Location ID in GraphQL format
        
    Raises:
        ShopifyAPIError: If location cannot be retrieved
    """
    from app.integrations.shopify.exceptions import ShopifyAPIError
    
    result = await shopify_admin_client.execute_query(GET_LOCATIONS_QUERY)
    
    locations = result.get("locations", {}).get("edges", [])
    
    if not locations or len(locations) == 0:
        raise ShopifyAPIError("No locations found in Shopify store")
    
    return locations[0]["node"]["id"]


async def set_inventory_quantity(
    inventory_item_id: str,
    quantity: int
) -> None:
    """
    Set inventory quantity for a variant.
    
    Args:
        inventory_item_id: Inventory item ID from variant
        quantity: Quantity to set
    """
    from app.integrations.shopify.exceptions import ShopifyAPIError
    from app.core.config import settings
    import logging
    logger = logging.getLogger(__name__)
    
    # Get location ID from settings
    location_id = settings.SHOPIFY_LOCATION_ID
    
    logger.info(f"SHOPIFY_LOCATION_ID from settings: [{location_id}] (length: {len(location_id) if location_id else 0})")
    
    if not location_id:
        logger.warning("SHOPIFY_LOCATION_ID not configured, skipping inventory update")
        return
    
    # Step 1: Activate inventory at the location (if not already activated)
    activate_mutation = """
    mutation activateInventory($inventoryItemId: ID!, $locationId: ID!) {
      inventoryActivate(inventoryItemId: $inventoryItemId, locationId: $locationId) {
        inventoryLevel {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    activate_variables = {
        "inventoryItemId": inventory_item_id,
        "locationId": location_id
    }
    
    try:
        activate_result = await shopify_admin_client.execute_mutation(activate_mutation, activate_variables)
        
        # Check for errors (ignore if already activated)
        if activate_result.get("inventoryActivate", {}).get("userErrors"):
            errors = activate_result["inventoryActivate"]["userErrors"]
            # Only log, don't fail - inventory might already be activated
            if errors:
                logger.info(f"Inventory activation response: {errors}")
    except Exception as e:
        logger.info(f"Inventory activation (might already be active): {str(e)}")
    
    # Step 2: Set inventory quantity using inventorySetQuantities
    set_mutation = """
    mutation setInventory($inventoryItemId: ID!, $locationId: ID!, $quantity: Int!) {
      inventorySetQuantities(input: {
        reason: "correction"
        name: "available"
        ignoreCompareQuantity: true
        quantities: [{
          inventoryItemId: $inventoryItemId
          locationId: $locationId
          quantity: $quantity
        }]
      }) {
        userErrors {
          field
          message
        }
        inventoryAdjustmentGroup {
          reason
        }
      }
    }
    """
    
    set_variables = {
        "inventoryItemId": inventory_item_id,
        "locationId": location_id,
        "quantity": quantity
    }
    
    result = await shopify_admin_client.execute_mutation(set_mutation, set_variables)
    
    # Check for errors
    if result.get("inventorySetQuantities", {}).get("userErrors"):
        errors = result["inventorySetQuantities"]["userErrors"]
        if errors:
            error_messages = [f"{err.get('field', 'unknown')}: {err.get('message', 'unknown error')}" for err in errors]
            raise ShopifyAPIError(f"Failed to set inventory: {', '.join(error_messages)}")
    
    logger.info(f"Successfully set inventory to {quantity}")


async def create_variant(
    product_id: str,
    ticket_name: str,
    ticket_type: str,
    price: float,
    inventory_quantity: int,
    description: Optional[str] = None,
    features: Optional[list[str]] = None,
    is_visible: bool = True,
    compare_at_price: Optional[float] = None,
    max_per_order: int = 10
) -> Dict[str, Any]:
    """
    Create a product variant (ticket) in Shopify.
    
    Args:
        product_id: Shopify product ID (legacy format)
        ticket_name: Name of the ticket
        ticket_type: Type of ticket (early_bird, regular, vip, etc.)
        price: Ticket price
        inventory_quantity: Available quantity
        description: Ticket description (HTML)
        features: List of ticket features
        is_visible: Whether ticket is visible
        compare_at_price: Original price for discount display
        max_per_order: Maximum tickets per order
        
    Returns:
        Formatted variant data
        
    Raises:
        ShopifyAPIError: If variant creation fails
    """
    from app.integrations.shopify.exceptions import ShopifyAPIError
    
    # Convert legacy product ID to GraphQL ID
    graphql_product_id = f"gid://shopify/Product/{product_id}"
    
    # Build ticket data for metafields
    ticket_data = {
        "ticket_type": ticket_type,
        "description": description,
        "features": features,
        "is_visible": is_visible,
        "max_per_order": max_per_order,
        "inventory_quantity": inventory_quantity  # Add this for capacity tracking
    }
    
    # Build metafields
    metafields = _build_variant_metafields(ticket_data)
    
    # Build variant input
    variant_input = {
        "optionValues": [{"optionName": "Title", "name": ticket_name}],
        "price": str(price),
        "inventoryPolicy": "DENY",
        "inventoryItem": {
            "tracked": True
        },
        "metafields": metafields
    }
    
    # Add compare at price if provided
    if compare_at_price is not None:
        variant_input["compareAtPrice"] = str(compare_at_price)
    
    # Execute mutation (bulk API expects array of variants)
    variables = {
        "productId": graphql_product_id,
        "variants": [variant_input]  # Wrap in array for bulk API
    }
    
    result = await shopify_admin_client.execute_mutation(CREATE_VARIANT_MUTATION, variables)
    
    # Check for errors
    if result.get("productVariantsBulkCreate", {}).get("userErrors"):
        errors = result["productVariantsBulkCreate"]["userErrors"]
        error_messages = [f"{err['field']}: {err['message']}" for err in errors]
        raise ShopifyAPIError(f"Failed to create variant: {', '.join(error_messages)}")
    
    # Extract variant data (first variant from array)
    variants = result.get("productVariantsBulkCreate", {}).get("productVariants", [])
    
    if not variants or len(variants) == 0:
        raise ShopifyAPIError("No variant data returned from Shopify")
    
    variant_data = variants[0]  # Get first (and only) variant
    
    # Set inventory quantity if specified
    if inventory_quantity > 0:
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Get inventory item ID from variant
            inventory_item_id = variant_data.get("inventoryItem", {}).get("id")
            logger.info(f"Inventory item ID: {inventory_item_id}")
            
            if not inventory_item_id:
                logger.warning("No inventory item ID returned from variant, skipping inventory update")
            else:
                # Set inventory quantity (no location query needed)
                logger.info(f"Attempting to set inventory to {inventory_quantity}")
                try:
                    await set_inventory_quantity(
                        inventory_item_id=inventory_item_id,
                        quantity=inventory_quantity
                    )
                    
                    # Update variant data with correct inventory quantity
                    variant_data["inventoryQuantity"] = inventory_quantity
                    logger.info(f"Inventory set successfully to {inventory_quantity}")
                except Exception as inv_error:
                    # Log but don't fail - variant is created, just inventory not set
                    logger.error(f"Failed to set inventory (non-fatal): {str(inv_error)}")
                    logger.info("Ticket created successfully, but inventory must be set manually in Shopify")
            
        except Exception as e:
            # Log error but don't fail the entire operation
            # Variant is created, just inventory not set
            logger.error(f"Error in inventory management (non-fatal): {str(e)}", exc_info=False)
    
    # Format and return response
    return _format_variant_response(variant_data)


async def update_variant(product_id: str, variant_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a Shopify variant (ticket) with partial data.
    Only provided fields will be updated.
    
    Args:
        product_id: Shopify product ID (legacy format)
        variant_id: Shopify variant ID (legacy format)
        update_data: Dictionary of fields to update
        
    Returns:
        Updated variant data
        
    Raises:
        ShopifyAPIError: If update fails
    """
    from app.integrations.shopify.exceptions import ShopifyAPIError
    import logging
    logger = logging.getLogger(__name__)
    
    # Convert legacy ID to GraphQL ID
    graphql_variant_id = f"gid://shopify/ProductVariant/{variant_id}"
    
    # Build variant input with only provided fields
    variant_input = {"id": graphql_variant_id}
    
    # Map update_data fields to Shopify variant fields
    if "ticket_name" in update_data and update_data["ticket_name"] is not None:
        variant_input["title"] = update_data["ticket_name"]
    
    if "price" in update_data and update_data["price"] is not None:
        variant_input["price"] = str(update_data["price"])
    
    if "compare_at_price" in update_data and update_data["compare_at_price"] is not None:
        variant_input["compareAtPrice"] = str(update_data["compare_at_price"])
    
    # Handle metafields separately
    metafields_to_update = []
    metafield_keys = ["description", "features", "is_visible", "max_per_order", "ticket_type", "inventory_quantity"]
    
    for key in metafield_keys:
        if key in update_data and update_data[key] is not None:
            metafield_type = "single_line_text_field"
            value = update_data[key]
            
            if key == "features":
                metafield_type = "json"
                value = json.dumps(value) if isinstance(value, list) else value
            elif key == "is_visible":
                metafield_type = "boolean"
                value = str(value).lower()
            elif key in ["max_per_order", "inventory_quantity"]:
                metafield_type = "number_integer"
                value = str(value)
            elif key == "description":
                metafield_type = "multi_line_text_field"
            
            metafields_to_update.append({
                "ownerId": graphql_variant_id,
                "namespace": "ticket",
                "key": key,
                "type": metafield_type,
                "value": str(value)
            })
    
    # Convert IDs to GraphQL format
    graphql_product_id = f"gid://shopify/Product/{product_id}"
    graphql_variant_id = f"gid://shopify/ProductVariant/{variant_id}"
    
    # Build variant input for bulk API
    variant_bulk_input = {"id": graphql_variant_id}
    
    # Map update_data fields to Shopify variant fields
    if "ticket_name" in update_data and update_data["ticket_name"] is not None:
        variant_bulk_input["title"] = update_data["ticket_name"]
    
    if "price" in update_data and update_data["price"] is not None:
        variant_bulk_input["price"] = str(update_data["price"])
    
    if "compare_at_price" in update_data and update_data["compare_at_price"] is not None:
        variant_bulk_input["compareAtPrice"] = str(update_data["compare_at_price"])
    
    # GraphQL mutation to update variant (using bulk API)
    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        productVariants {
          id
          legacyResourceId
          title
          price
          compareAtPrice
          inventoryQuantity
          metafields(first: 20, namespace: "ticket") {
            edges {
              node {
                key
                value
                type
              }
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "productId": graphql_product_id,
        "variants": [variant_bulk_input]  # Bulk API expects array
    }
    
    result = await shopify_admin_client.execute_mutation(mutation, variables)
    
    # Check for errors
    if result.get("productVariantsBulkUpdate", {}).get("userErrors"):
        errors = result["productVariantsBulkUpdate"]["userErrors"]
        if errors:
            error_messages = [f"{err.get('field', 'unknown')}: {err.get('message', 'unknown error')}" for err in errors]
            raise ShopifyAPIError(f"Failed to update variant: {', '.join(error_messages)}")
    
    # Get updated variant data
    variants = result.get("productVariantsBulkUpdate", {}).get("productVariants", [])
    if not variants:
        raise ShopifyAPIError(f"No variant data returned after update")
    
    variant_data = variants[0]  # Get first (and only) variant
    
    # Update metafields if any
    if metafields_to_update:
        metafields_mutation = """
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
          metafieldsSet(metafields: $metafields) {
            metafields {
              id
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        
        metafields_result = await shopify_admin_client.execute_mutation(
            metafields_mutation,
            {"metafields": metafields_to_update}
        )
        
        if metafields_result.get("metafieldsSet", {}).get("userErrors"):
            errors = metafields_result["metafieldsSet"]["userErrors"]
            if errors:
                logger.warning(f"Some metafields failed to update: {errors}")
    
    # Handle inventory update if provided
    if "inventory_quantity" in update_data and update_data["inventory_quantity"] is not None:
        # Get variant data to find inventory item ID
        logger.info(f"Inventory quantity update requested: {update_data['inventory_quantity']}")
        # TODO: Implement inventory update via set_inventory_quantity if needed
    
    # Return formatted variant response
    if variant_data:
        logger.info(f"Successfully updated variant {variant_id}")
        # Format the response - variant_data already has the structure we need
        return _format_variant_response(variant_data)
    else:
        raise ShopifyAPIError(f"Failed to update variant {variant_id}")


async def delete_variant(product_id: str, variant_id: str) -> bool:
    """
    Delete a Shopify variant using bulk delete mutation.
    
    Args:
        product_id: Shopify product ID (legacy format)
        variant_id: Shopify variant ID (legacy format)
        
    Returns:
        True if deletion successful
        
    Raises:
        ShopifyAPIError: If deletion fails
    """
    from app.integrations.shopify.exceptions import ShopifyAPIError
    import logging
    logger = logging.getLogger(__name__)
    
    # Convert legacy IDs to GraphQL IDs
    graphql_product_id = f"gid://shopify/Product/{product_id}"
    graphql_variant_id = f"gid://shopify/ProductVariant/{variant_id}"
    
    # Use productVariantsBulkDelete mutation (available in 2025-01)
    mutation = """
    mutation deleteVariants($productId: ID!, $variantsIds: [ID!]!) {
      productVariantsBulkDelete(productId: $productId, variantsIds: $variantsIds) {
        product {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "productId": graphql_product_id,
        "variantsIds": [graphql_variant_id]
    }
    
    result = await shopify_admin_client.execute_mutation(mutation, variables)
    
    # Check for errors
    if result.get("productVariantsBulkDelete", {}).get("userErrors"):
        errors = result["productVariantsBulkDelete"]["userErrors"]
        if errors:
            error_messages = [f"{err.get('field', 'unknown')}: {err.get('message', 'unknown error')}" for err in errors]
            raise ShopifyAPIError(f"Failed to delete variant: {', '.join(error_messages)}")
    
    product = result.get("productVariantsBulkDelete", {}).get("product")
    
    if product:
        logger.info(f"Successfully deleted variant {variant_id} from product {product_id}")
        return True
    else:
        raise ShopifyAPIError(f"Failed to delete variant {variant_id}")


async def list_variants(product_id: str) -> list[Dict[str, Any]]:
    """
    List all variants for a product.
    
    Args:
        product_id: Shopify product ID (legacy format)
        
    Returns:
        List of variant data dictionaries
        
    Raises:
        ShopifyAPIError: If fetching fails
    """
    from app.integrations.shopify.exceptions import ShopifyAPIError
    import logging
    logger = logging.getLogger(__name__)
    
    # Convert legacy ID to GraphQL ID
    graphql_product_id = f"gid://shopify/Product/{product_id}"
    
    # GraphQL query to get all variants with inventory
    query = """
    query getVariants($id: ID!) {
      product(id: $id) {
        id
        variants(first: 50) {
          edges {
            node {
              id
              legacyResourceId
              title
              price
              inventoryQuantity
              inventoryItem {
                id
                tracked
              }
              metafields(first: 20, namespace: "ticket") {
                edges {
                  node {
                    key
                    value
                    type
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    
    variables = {"id": graphql_product_id}
    
    result = await shopify_admin_client.execute_query(query, variables)
    
    product = result.get("product")
    if not product:
        raise ShopifyAPIError(f"Product {product_id} not found")
    
    variants = []
    for edge in product.get("variants", {}).get("edges", []):
        variant = edge["node"]
        
        # Parse metafields
        metafields_data = variant.get("metafields", {})
        parsed_metafields = _parse_variant_metafields(metafields_data)
        
        # Get current available inventory
        available = variant.get("inventoryQuantity", 0)
        
        # Calculate capacity (use metafield if exists and > 0, otherwise use current inventory)
        # This provides backwards compatibility for tickets created before metafield was added
        # and fixes tickets where metafield was incorrectly saved as 0
        metafield_capacity = parsed_metafields.get("inventory_quantity", 0)
        capacity = metafield_capacity if metafield_capacity > 0 else available
        
        # Calculate sold count (capacity - available)
        sold = max(0, capacity - available)
        
        # Determine status
        is_visible = parsed_metafields.get("is_visible", True)
        if not is_visible:
            status = "hidden"
        elif available == 0:
            status = "sold_out"
        else:
            status = "active"
        
        # Calculate revenue
        price = float(variant["price"])
        revenue = sold * price
        
        variant_data = {
            "shopify_variant_id": variant["legacyResourceId"],
            "ticket_name": variant["title"],
            "ticket_type": parsed_metafields.get("ticket_type", "regular"),
            "price": price,
            "capacity": capacity,
            "sold": sold,
            "revenue": revenue,
            "available": available,
            "status": status,
        }
        
        variants.append(variant_data)
    
    logger.info(f"Retrieved {len(variants)} variants for product {product_id}")
    return variants


def _parse_variant_metafields(metafields_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse metafields from GraphQL response.
    
    Args:
        metafields_data: Metafields data from GraphQL
        
    Returns:
        Dictionary of metafield key-value pairs
    """
    metafields = {}
    
    if not metafields_data or not metafields_data.get("edges"):
        return metafields
    
    for edge in metafields_data["edges"]:
        node = edge.get("node", {})
        key = node.get("key")
        value = node.get("value")
        field_type = node.get("type")
        
        if key and value is not None:
            # Parse based on type
            if field_type == "json":
                try:
                    metafields[key] = json.loads(value)
                except json.JSONDecodeError:
                    metafields[key] = value
            elif field_type == "boolean":
                metafields[key] = value.lower() == "true"
            elif field_type == "number_integer":
                metafields[key] = int(value)
            else:
                metafields[key] = value
    
    return metafields


def _format_variant_response(variant_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format variant data into ticket response structure.
    
    Args:
        variant_data: Raw variant data from Shopify
        
    Returns:
        Formatted ticket data
    """
    metafields = _parse_variant_metafields(variant_data.get("metafields", {}))
    
    # Calculate sold count and available quantity
    inventory_quantity = variant_data.get("inventoryQuantity", 0)
    
    return {
        "shopify_variant_id": variant_data.get("legacyResourceId"),
        "ticket_name": variant_data.get("title"),
        "ticket_type": metafields.get("ticket_type"),
        "description": metafields.get("description"),
        "features": metafields.get("features"),
        "is_visible": metafields.get("is_visible", True),
        "price": float(variant_data.get("price", 0)),
        "compare_at_price": float(variant_data.get("compareAtPrice")) if variant_data.get("compareAtPrice") else None,
        "inventory_quantity": inventory_quantity,
        "max_per_order": metafields.get("max_per_order", 10),
        "sold_count": 0,  # TODO: Calculate from orders
        "available_quantity": inventory_quantity
    }
