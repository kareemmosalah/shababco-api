"""
Shopify product operations.
Handles fetching and creating products with metafields.
"""
import json
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
    handle
    status
    totalInventory
    tags
    images(first: 20) {
      edges {
        node {
          url
          altText
        }
      }
    }
    metafields(first: 20, namespace: "event") {
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
        handle
        status
        totalInventory
        tags
        images(first: 20) {
          edges {
            node {
              url
              altText
            }
          }
        }
        metafields(first: 20, namespace: "event") {
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
      handle
      status
      totalInventory
      tags
      images(first: 20) {
        edges {
          node {
            url
            altText
          }
        }
      }
      metafields(first: 20, namespace: "event") {
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
    
    # Parse images from metafields (since we store them there during creation)
    # In the future, we can also check product.images if we add media separately
    cover_image = metafields.get("cover_image")
    
    # Parse gallery_images from JSON metafield
    gallery_images = None
    gallery_images_json = metafields.get("gallery_images")
    if gallery_images_json:
        try:
            import json
            gallery_images = json.loads(gallery_images_json)
        except (json.JSONDecodeError, TypeError):
            gallery_images = None
    
    return {
        "shopify_product_id": product_data.get("legacyResourceId"),
        "product_type": product_data.get("productType", "event"),  # Default to "event"
        # Event Information
        "title": product_data.get("title"),
        "subtitle": metafields.get("subtitle"),
        "description": product_data.get("descriptionHtml"),
        "category": metafields.get("category"),
        "tags": product_data.get("tags"),
        "cover_image": cover_image,
        "gallery_images": gallery_images,
        # Location & Time
        "venue_name": metafields.get("venue_name"),
        "city": metafields.get("city"),
        "address": metafields.get("address"),
        "country": metafields.get("country"),
        "location_link": metafields.get("location_link"),
        "start_datetime": metafields.get("start_datetime"),
        "end_datetime": metafields.get("end_datetime"),
        # Organizer
        "organizer_name": metafields.get("organizer_name"),
        # SEO
        "seo_slug": product_data.get("handle"),
        # Status & Inventory
        "status": product_data.get("status", "").lower(),
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
    subtitle: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    cover_image: Optional[str] = None,
    gallery_images: Optional[List[str]] = None,
    venue_name: Optional[str] = None,
    city: Optional[str] = None,
    address: Optional[str] = None,
    country: Optional[str] = None,
    location_link: Optional[str] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
    organizer_name: Optional[str] = None,
    seo_slug: Optional[str] = None,
    status: str = "DRAFT"
) -> Dict[str, Any]:
    """
    Create a new product with event metafields.
    
    Args:
        title: Product title
        description: Product description (HTML supported)
        subtitle: Event subtitle/tagline
        category: Event category
        tags: Event tags
        cover_image: Cover image URL
        gallery_images: Gallery image URLs
        venue_name: Venue name
        city: Event city
        address: Full address
        country: Country
        location_link: Google Maps or location URL
        start_datetime: Event start datetime in ISO format
        end_datetime: Event end datetime in ISO format
        organizer_name: Organizer name
        seo_slug: SEO slug (URL handle)
        status: Product status (ACTIVE, DRAFT, ARCHIVED)
        
    Returns:
        Created product data formatted as ShababcoEvent
        
    Raises:
        ShopifyValidationError: If validation fails
    """
    # Build metafields array
    metafields = []
    
    # Event Information metafields
    if subtitle:
        metafields.append({
            "namespace": "event",
            "key": "subtitle",
            "value": subtitle,
            "type": "single_line_text_field"
        })
    if category:
        metafields.append({
            "namespace": "event",
            "key": "category",
            "value": category,
            "type": "single_line_text_field"
        })
    
    # Location & Time metafields
    if venue_name:
        metafields.append({
            "namespace": "event",
            "key": "venue_name",
            "value": venue_name,
            "type": "single_line_text_field"
        })
    if city:
        metafields.append({
            "namespace": "event",
            "key": "city",
            "value": city,
            "type": "single_line_text_field"
        })
    if address:
        metafields.append({
            "namespace": "event",
            "key": "address",
            "value": address,
            "type": "multi_line_text_field"
        })
    if country:
        metafields.append({
            "namespace": "event",
            "key": "country",
            "value": country,
            "type": "single_line_text_field"
        })
    if location_link:
        metafields.append({
            "namespace": "event",
            "key": "location_link",
            "value": location_link,
            "type": "url"
        })
    if start_datetime:
        metafields.append({
            "namespace": "event",
            "key": "start_datetime",
            "value": start_datetime,
            "type": "date_time"
        })
    if end_datetime:
        metafields.append({
            "namespace": "event",
            "key": "end_datetime",
            "value": end_datetime,
            "type": "date_time"
        })
    
    # Organizer metafield
    if organizer_name:
        metafields.append({
            "namespace": "event",
            "key": "organizer_name",
            "value": organizer_name,
            "type": "single_line_text_field"
        })
    
    # Note: Images cannot be added during product creation via GraphQL ProductInput
    # They need to be added separately using productCreateMedia mutation
    # For now, we'll store image URLs as metafields and add them in a future update
    
    # Store cover_image as metafield if provided
    if cover_image:
        metafields.append({
            "namespace": "event",
            "key": "cover_image",
            "value": cover_image,
            "type": "url"
        })
    
    # Store gallery_images as JSON metafield if provided
    if gallery_images:
        import json
        metafields.append({
            "namespace": "event",
            "key": "gallery_images",
            "value": json.dumps(gallery_images),
            "type": "json"
        })
    
    # Build product input
    product_input = {
        "title": title,
        "status": status.upper(),
        "productType": "event",
        "metafields": metafields,
    }
    
    # Add optional fields
    if description:
        product_input["descriptionHtml"] = description
    
    if tags:
        product_input["tags"] = tags
    
    if seo_slug:
        product_input["handle"] = seo_slug
    
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


async def delete_product(product_id: str) -> bool:
    """
    Delete a Shopify product.
    
    Args:
        product_id: Shopify product ID (legacy format)
        
    Returns:
        True if deletion successful
        
    Raises:
        ShopifyAPIError: If deletion fails
    """
    from .exceptions import ShopifyAPIError
    
    # Convert legacy ID to GraphQL ID
    graphql_product_id = f"gid://shopify/Product/{product_id}"
    
    # GraphQL mutation to delete product
    mutation = """
    mutation deleteProduct($id: ID!) {
      productDelete(input: {id: $id}) {
        deletedProductId
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {"id": graphql_product_id}
    
    result = await shopify_admin_client.execute_mutation(mutation, variables)
    
    # Check for errors
    if result.get("productDelete", {}).get("userErrors"):
        errors = result["productDelete"]["userErrors"]
        if errors:
            error_messages = [f"{err.get('field', 'unknown')}: {err.get('message', 'unknown error')}" for err in errors]
            raise ShopifyAPIError(f"Failed to delete product: {', '.join(error_messages)}")
    
    deleted_id = result.get("productDelete", {}).get("deletedProductId")
    
    if deleted_id:
        logger.info(f"Successfully deleted product {product_id}")
        return True
    else:
        raise ShopifyAPIError(f"Failed to delete product {product_id}")


async def update_product_status(product_id: str, status: str) -> Dict[str, Any]:
    """
    Update a Shopify product's status.
    
    Args:
        product_id: Shopify product ID (legacy format)
        status: New status (draft, active, archived)
        
    Returns:
        Updated product data
        
    Raises:
        ShopifyAPIError: If update fails
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Convert legacy ID to GraphQL ID
    graphql_product_id = f"gid://shopify/Product/{product_id}"
    
    # GraphQL mutation to update product status
    mutation = """
    mutation updateProductStatus($id: ID!, $status: ProductStatus!) {
      productUpdate(input: {id: $id, status: $status}) {
        product {
          id
          legacyResourceId
          status
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {
        "id": graphql_product_id,
        "status": status.upper()
    }
    
    result = await shopify_admin_client.execute_mutation(mutation, variables)
    
    # Check for errors
    if result.get("productUpdate", {}).get("userErrors"):
        errors = result["productUpdate"]["userErrors"]
        if errors:
            error_messages = [f"{err.get('field', 'unknown')}: {err.get('message', 'unknown error')}" for err in errors]
            raise ShopifyAPIError(f"Failed to update product status: {', '.join(error_messages)}")
    
    product = result.get("productUpdate", {}).get("product")
    
    if product:
        logger.info(f"Successfully updated product {product_id} status to {status}")
        return product
    else:
        raise ShopifyAPIError(f"Failed to update product {product_id} status")


async def update_product(product_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a Shopify product with partial data.
    Only provided fields will be updated.
    
    Args:
        product_id: Shopify product ID (legacy format)
        update_data: Dictionary of fields to update
        
    Returns:
        Updated product data
        
    Raises:
        ShopifyAPIError: If update fails
    """
    from .exceptions import ShopifyAPIError
    
    # Convert legacy ID to GraphQL ID
    graphql_product_id = f"gid://shopify/Product/{product_id}"
    
    # Build product input with only provided fields
    product_input = {"id": graphql_product_id}
    
    # Map update_data fields to Shopify fields
    if "title" in update_data and update_data["title"] is not None:
        product_input["title"] = update_data["title"]
    
    if "description" in update_data and update_data["description"] is not None:
        product_input["descriptionHtml"] = update_data["description"]
    
    if "tags" in update_data and update_data["tags"] is not None:
        product_input["tags"] = update_data["tags"]
    
    if "seo_slug" in update_data and update_data["seo_slug"] is not None:
        product_input["handle"] = update_data["seo_slug"]
    
    if "status" in update_data and update_data["status"] is not None:
        product_input["status"] = update_data["status"].upper()
    
    # Handle metafields separately if needed
    metafields_to_update = []
    metafield_keys = ["subtitle", "category", "cover_image", "gallery_images", "venue_name", 
                      "city", "address", "country", "location_link", "start_datetime", 
                      "end_datetime", "organizer_name"]
    
    for key in metafield_keys:
        if key in update_data and update_data[key] is not None:
            metafield_type = "single_line_text_field"
            value = update_data[key]
            
            if key == "gallery_images":
                metafield_type = "json"
                value = json.dumps(value) if isinstance(value, list) else value
            
            metafields_to_update.append({
                "ownerId": graphql_product_id,
                "namespace": "event",
                "key": key,
                "type": metafield_type,
                "value": str(value)
            })
    
    # GraphQL mutation to update product
    mutation = """
    mutation productUpdate($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          legacyResourceId
          title
          descriptionHtml
          status
        }
        userErrors {
          field
          message
        }
      }
    }
    """
    
    variables = {"input": product_input}
    
    result = await shopify_admin_client.execute_mutation(mutation, variables)
    
    # Check for errors
    if result.get("productUpdate", {}).get("userErrors"):
        errors = result["productUpdate"]["userErrors"]
        if errors:
            error_messages = [f"{err.get('field', 'unknown')}: {err.get('message', 'unknown error')}" for err in errors]
            raise ShopifyAPIError(f"Failed to update product: {', '.join(error_messages)}")
    
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
    
    product = result.get("productUpdate", {}).get("product")
    
    if product:
        logger.info(f"Successfully updated product {product_id}")
        # Fetch full product data to return
        return await fetch_product(product_id)
    else:
        raise ShopifyAPIError(f"Failed to update product {product_id}")
