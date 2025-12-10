"""
Shopify webhook endpoints.
Handles incoming webhooks from Shopify.
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Header, status

from app.core.config import settings
from app.integrations.shopify.webhooks import verify_webhook_signature, generate_correlation_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/shopify", tags=["Shopify Webhooks"])


@router.post("/order-created")
async def order_created_webhook(
    request: Request,
    x_shopify_hmac_sha256: str = Header(..., alias="X-Shopify-Hmac-SHA256"),
    x_shopify_shop_domain: str = Header(None, alias="X-Shopify-Shop-Domain"),
    x_shopify_topic: str = Header(None, alias="X-Shopify-Topic"),
) -> Dict[str, Any]:
    """
    Handle Shopify order/create webhook.
    
    For Milestone 1:
    - Validates HMAC signature
    - Logs payload with correlation ID
    - No database writes yet
    
    Headers:
        X-Shopify-Hmac-SHA256: HMAC signature for verification
        X-Shopify-Shop-Domain: Store domain
        X-Shopify-Topic: Webhook topic (orders/create)
    """
    # Generate correlation ID for tracking
    correlation_id = generate_correlation_id()
    
    logger.info(
        f"[{correlation_id}] Received webhook - "
        f"Topic: {x_shopify_topic}, Shop: {x_shopify_shop_domain}"
    )
    
    # Read raw request body for HMAC verification
    body = await request.body()
    
    # Verify webhook signature
    if not settings.SHOPIFY_WEBHOOK_SECRET:
        logger.error(f"[{correlation_id}] SHOPIFY_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured"
        )
    
    is_valid = verify_webhook_signature(
        data=body,
        hmac_header=x_shopify_hmac_sha256,
        secret=settings.SHOPIFY_WEBHOOK_SECRET
    )
    
    if not is_valid:
        logger.warning(
            f"[{correlation_id}] Invalid webhook signature from {x_shopify_shop_domain}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse JSON payload
    try:
        import json
        payload = json.loads(body.decode('utf-8'))
    except Exception as e:
        logger.error(f"[{correlation_id}] Failed to parse webhook payload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Log payload for Milestone 1 (no DB writes yet)
    logger.info(
        f"[{correlation_id}] Order created webhook payload: "
        f"Order ID: {payload.get('id')}, "
        f"Order Number: {payload.get('order_number')}, "
        f"Total: {payload.get('total_price')} {payload.get('currency')}, "
        f"Customer: {payload.get('customer', {}).get('email')}"
    )
    
    # Log full payload at debug level
    logger.debug(f"[{correlation_id}] Full payload: {json.dumps(payload, indent=2)}")
    
    # Health check logging
    logger.info(f"[{correlation_id}] Webhook processed successfully")
    
    return {
        "status": "received",
        "correlation_id": correlation_id,
        "message": "Webhook received and logged successfully"
    }


@router.get("/health")
async def webhook_health() -> Dict[str, str]:
    """
    Health check endpoint for webhook receiver.
    
    Returns:
        Status of webhook configuration
    """
    has_secret = bool(settings.SHOPIFY_WEBHOOK_SECRET)
    
    return {
        "status": "healthy",
        "webhook_secret_configured": str(has_secret),
        "store_domain": settings.SHOPIFY_STORE_DOMAIN or "not configured"
    }
