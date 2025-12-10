"""
Shopify integration module.
Provides access to Shopify Admin API for product management.
"""
from .admin_client import ShopifyAdminClient, shopify_admin_client
from .products import fetch_product, list_products, create_product
from .exceptions import (
    ShopifyAPIError,
    ShopifyAuthError,
    ShopifyRateLimitError,
    ShopifyNotFoundError,
    ShopifyValidationError,
)

__all__ = [
    "ShopifyAdminClient",
    "shopify_admin_client",
    "fetch_product",
    "list_products",
    "create_product",
    "ShopifyAPIError",
    "ShopifyAuthError",
    "ShopifyRateLimitError",
    "ShopifyNotFoundError",
    "ShopifyValidationError",
]
