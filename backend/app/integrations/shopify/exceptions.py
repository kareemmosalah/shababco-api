"""
Custom exceptions for Shopify integration.
"""


class ShopifyAPIError(Exception):
    """Base exception for Shopify API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class ShopifyAuthError(ShopifyAPIError):
    """Exception raised for authentication failures."""
    pass


class ShopifyRateLimitError(ShopifyAPIError):
    """Exception raised when rate limit is exceeded."""
    pass


class ShopifyNotFoundError(ShopifyAPIError):
    """Exception raised when a resource is not found."""
    pass


class ShopifyValidationError(ShopifyAPIError):
    """Exception raised for validation errors."""
    pass
