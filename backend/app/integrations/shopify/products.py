"""
Shopify product operations.
Handles fetching and creating products with metafields.
"""
import logging
from typing import Dict, Any, List, Optional

from .admin_client import shopify_admin_client
from .exceptions import ShopifyNotFoundError, ShopifyValidationError

logger = logging.getLogger(__name__)


# GraphQL query to fetch a single product with metafields
FETCH_PRODUCT_QUERY = """
query getProduct($id: ID!) {
  product(id: $id) {
    id
    legacyResourceId
    title
    descriptionHtml
    status
    totalInventory
    metafields(first: 10, namespace: "event") {
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
"""

# GraphQL query to list products with metafields
LIST_PRODUCTS_QUERY = """
query listProducts($first: Int!, $query: String, $after: String) {
  products(first: $first, query: $query, after: $after) {
    edges {
      node {
        id
        legacyResourceId
        title
        descriptionHtml
        status
        totalInventory
        metafields(first: 10, namespace: "event") {
          edges {
            node {
              key
              value
              type
            }
          }
        }
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

# GraphQL mutation to create a product with metafields
CREATE_PRODUCT_MUTATION = """
mutation createProduct($input: ProductInput!) {
  productCreate(input: $input) {
    product {
      id
      legacyResourceId
      title
      descriptionHtml
      status
      totalInventory
      metafields(first: 10, namespace: "event") {
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


def _parse_metafields(metafields_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Parse metafields from GraphQL response.
    
    Args:
        metafields_data: Metafields data from GraphQL response
        
    Returns:
        Dictionary of metafield key-value pairs
    """
    metafields = {}
    if metafields_data and "edges" in metafields_data:
        for edge in metafields_data["edges"]:
            node = edge.get("node", {})
            key = node.get("key")
            value = node.get("value")
            if key and value is not None:
                metafields[key] = value
    return metafields


def _format_product_response(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format product data into ShababcoEvent structure.
    
    Args:
        product_data: Raw product data from Shopify
        
    Returns:
        Formatted event data matching ShababcoEvent type
    """
    if not product_data:
        return None
    
    metafields = _parse_metafields(product_data.get("metafields", {}))
    
    return {
        "shopify_product_id": product_data.get("legacyResourceId"),
        "title": product_data.get("title"),
        "description": product_data.get("descriptionHtml"),
        "status": product_data.get("status", "").lower(),
        "city": metafields.get("city"),
        "start_datetime": metafields.get("start_datetime"),
        "total_tickets": product_data.get("totalInventory", 0),
    }


async def fetch_product(product_id: str) -> Dict[str, Any]:
    """
    Fetch a single product by ID with metafields.
    
    Args:
        product_id: Shopify product ID (can be GID or legacy ID)
        
    Returns:
        Product data formatted as ShababcoEvent
        
    Raises:
        ShopifyNotFoundError: If product not found
    """
    # Convert legacy ID to GID if needed
    if not product_id.startswith("gid://"):
        product_id = f"gid://shopify/Product/{product_id}"
    
    variables = {"id": product_id}
    
    try:
        data = await shopify_admin_client.execute_query(FETCH_PRODUCT_QUERY, variables)
        product = data.get("product")
        
        if not product:
            raise ShopifyNotFoundError(f"Product {product_id} not found")
        
        return _format_product_response(product)
        
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {str(e)}")
        raise


async def list_products(
    limit: int = 50,
    query: Optional[str] = None,
    cursor: Optional[str] = None
) -> Dict[str, Any]:
    """
    List products with optional filtering.
    
    Args:
        limit: Maximum number of products to return (max 250)
        query: Shopify search query (e.g., "product_type:event")
        cursor: Pagination cursor
        
    Returns:
        Dictionary with products list and pagination info
    """
    variables = {
        "first": min(limit, 250),
        "query": query,
        "after": cursor
    }
    
    try:
        data = await shopify_admin_client.execute_query(LIST_PRODUCTS_QUERY, variables)
        products_data = data.get("products", {})
        
        products = []
        for edge in products_data.get("edges", []):
            product = edge.get("node")
            if product:
                formatted = _format_product_response(product)
                if formatted:
                    products.append(formatted)
        
        page_info = products_data.get("pageInfo", {})
        
        return {
            "products": products,
            "has_next_page": page_info.get("hasNextPage", False),
            "end_cursor": page_info.get("endCursor"),
        }
        
    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        raise


async def create_product(
    title: str,
    description: Optional[str] = None,
    city: Optional[str] = None,
    start_datetime: Optional[str] = None,
    status: str = "DRAFT"
) -> Dict[str, Any]:
    """
    Create a new product with event metafields.
    
    Args:
        title: Product title
        description: Product description (HTML supported)
        city: Event city (stored as metafield)
        start_datetime: Event start datetime in ISO format (stored as metafield)
        status: Product status (ACTIVE, DRAFT, ARCHIVED)
        
    Returns:
        Created product data formatted as ShababcoEvent
        
    Raises:
        ShopifyValidationError: If validation fails
    """
    # Build metafields array
    metafields = []
    if city:
        metafields.append({
            "namespace": "event",
            "key": "city",
            "value": city,
            "type": "single_line_text_field"
        })
    if start_datetime:
        metafields.append({
            "namespace": "event",
            "key": "start_datetime",
            "value": start_datetime,
            "type": "date_time"
        })
    
    # Build product input
    product_input = {
        "title": title,
        "status": status.upper(),
        "productType": "event",
        "tags": ["shababco-event"],
        "metafields": metafields,
    }
    
    # Add description if provided
    if description:
        product_input["descriptionHtml"] = description
    
    variables = {"input": product_input}
    
    try:
        data = await shopify_admin_client.execute_mutation(CREATE_PRODUCT_MUTATION, variables)
        result = data.get("productCreate", {})
        
        # Check for user errors
        user_errors = result.get("userErrors", [])
        if user_errors:
            error_messages = [f"{err.get('field')}: {err.get('message')}" for err in user_errors]
            raise ShopifyValidationError(
                f"Product creation failed: {', '.join(error_messages)}"
            )
        
        product = result.get("product")
        if not product:
            raise ShopifyValidationError("Product creation failed: No product returned")
        
        return _format_product_response(product)
        
    except ShopifyValidationError:
        raise
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise
