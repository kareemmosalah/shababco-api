"""
Update is_featured metafield for a product.
"""
from .admin_client import shopify_admin_client
from .exceptions import ShopifyAPIError
import logging

logger = logging.getLogger(__name__)


async def update_is_featured(product_id: str, is_featured: bool) -> bool:
    """
    Update the is_featured metafield for a product.
    
    Args:
        product_id: Shopify product ID (legacy format)
        is_featured: Whether the event should be featured
        
    Returns:
        True if update successful
        
    Raises:
        ShopifyAPIError: If update fails
    """
    # Convert legacy ID to GraphQL ID
    graphql_product_id = f"gid://shopify/Product/{product_id}"
    
    # GraphQL mutation to set metafield
    mutation = """
    mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields {
          id
          namespace
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
            "ownerId": graphql_product_id,
            "namespace": "custom",
            "key": "is_featured",
            "type": "boolean",
            "value": str(is_featured).lower()  # "true" or "false"
        }]
    }
    
    result = await shopify_admin_client.execute_mutation(mutation, variables)
    
    # Check for errors
    if result.get("metafieldsSet", {}).get("userErrors"):
        errors = result["metafieldsSet"]["userErrors"]
        if errors:
            error_messages = [f"{err.get('field', 'unknown')}: {err.get('message', 'unknown error')}" for err in errors]
            raise ShopifyAPIError(f"Failed to update is_featured: {', '.join(error_messages)}")
    
    metafields = result.get("metafieldsSet", {}).get("metafields", [])
    
    if metafields:
        logger.info(f"Successfully updated is_featured={is_featured} for product {product_id}")
        return True
    else:
        raise ShopifyAPIError(f"Failed to update is_featured for product {product_id}")
