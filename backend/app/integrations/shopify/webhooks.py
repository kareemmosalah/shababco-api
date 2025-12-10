"""
Shopify webhook utilities.
Handles webhook signature validation and processing.
"""
import hmac
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def verify_webhook_signature(
    data: bytes,
    hmac_header: str,
    secret: str
) -> bool:
    """
    Verify Shopify webhook HMAC signature.
    
    Args:
        data: Raw request body as bytes
        hmac_header: HMAC signature from X-Shopify-Hmac-SHA256 header
        secret: Webhook secret key
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Compute HMAC-SHA256 of the request body
        computed_hmac = hmac.new(
            secret.encode('utf-8'),
            data,
            hashlib.sha256
        ).digest()
        
        # Shopify sends the HMAC as base64-encoded
        import base64
        computed_hmac_b64 = base64.b64encode(computed_hmac).decode('utf-8')
        
        # Compare using constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed_hmac_b64, hmac_header)
        
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return False


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID for webhook tracking.
    
    Returns:
        UUID string for correlation tracking
    """
    import uuid
    return str(uuid.uuid4())
