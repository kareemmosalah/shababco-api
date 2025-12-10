"""
Shopify Admin API GraphQL client.
Handles GraphQL queries and mutations to Shopify Admin API.
"""
import logging
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings
from .exceptions import (
    ShopifyAPIError,
    ShopifyAuthError,
    ShopifyRateLimitError,
    ShopifyNotFoundError,
)

logger = logging.getLogger(__name__)


class ShopifyAdminClient:
    """Client for Shopify Admin API using GraphQL."""
    
    def __init__(self):
        self.graphql_url = settings.shopify_graphql_url
        self.access_token = settings.SHOPIFY_ADMIN_API_TOKEN
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }
    
    async def execute_query(
        self,
        query: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL query against Shopify Admin API.
        
        Args:
            query: GraphQL query string
            variables: Optional variables for the query
            
        Returns:
            Response data from Shopify
            
        Raises:
            ShopifyAPIError: For general API errors
            ShopifyAuthError: For authentication failures
            ShopifyRateLimitError: When rate limit is exceeded
        """
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.graphql_url,
                    json=payload,
                    headers=self.headers
                )
                
                # Handle HTTP errors
                if response.status_code == 401:
                    logger.error("Shopify authentication failed")
                    raise ShopifyAuthError(
                        "Authentication failed. Check your access token.",
                        status_code=401
                    )
                
                if response.status_code == 429:
                    logger.warning("Shopify rate limit exceeded")
                    raise ShopifyRateLimitError(
                        "Rate limit exceeded. Please try again later.",
                        status_code=429
                    )
                
                if response.status_code >= 400:
                    logger.error(f"Shopify API error: {response.status_code}")
                    raise ShopifyAPIError(
                        f"API request failed with status {response.status_code}",
                        status_code=response.status_code,
                        response_data=response.json() if response.text else None
                    )
                
                data = response.json()
                
                # Handle GraphQL errors
                if "errors" in data:
                    error_messages = [err.get("message", "") for err in data["errors"]]
                    logger.error(f"GraphQL errors: {error_messages}")
                    raise ShopifyAPIError(
                        f"GraphQL errors: {', '.join(error_messages)}",
                        response_data=data
                    )
                
                return data.get("data", {})
                
        except httpx.TimeoutException:
            logger.error("Shopify API request timed out")
            raise ShopifyAPIError("Request timed out")
        except httpx.RequestError as e:
            logger.error(f"Shopify API request error: {str(e)}")
            raise ShopifyAPIError(f"Request failed: {str(e)}")
    
    async def execute_mutation(
        self,
        mutation: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a GraphQL mutation against Shopify Admin API.
        
        Args:
            mutation: GraphQL mutation string
            variables: Optional variables for the mutation
            
        Returns:
            Response data from Shopify
        """
        return await self.execute_query(mutation, variables)


# Global client instance
shopify_admin_client = ShopifyAdminClient()
