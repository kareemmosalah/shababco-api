"""
Admin events endpoints (CRUD).
Handles event management through Shopify integration.
"""
import logging
from typing import Optional, Annotated
from fastapi import APIRouter, HTTPException, Query, status, Depends

from app.schemas.event import EventCreate, ShababcoEvent, EventListResponse
from app.integrations.shopify import (
    fetch_product,
    list_products,
    create_product,
    ShopifyNotFoundError,
    ShopifyValidationError,
    ShopifyAPIError,
)
from app.api.deps import CurrentUser, get_current_active_superuser
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Admin Events"])


@router.get("", response_model=EventListResponse)
async def get_events(
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=250, description="Number of events to return"),
    cursor: Optional[str] = Query(default=None, description="Pagination cursor"),
    product_type: str = Query(default="event", description="Filter by product type")
):
    """
    List all events from Shopify.
    
    Fetches products with product_type='event' and returns them as ShababcoEvent objects.
    """
    try:
        # Build Shopify query filter
        query = f"product_type:{product_type}"
        
        result = await list_products(limit=limit, query=query, cursor=cursor)
        
        return EventListResponse(
            events=result["products"],
            has_next_page=result["has_next_page"],
            end_cursor=result["end_cursor"]
        )
        
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while listing events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch events from Shopify: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while listing events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/{product_id}", response_model=ShababcoEvent)
async def get_event(current_user: CurrentUser, product_id: str):
    """
    Get a single event by Shopify product ID.
    
    Args:
        product_id: Shopify product ID (legacy ID or GID)
    """
    try:
        event = await fetch_product(product_id)
        return event
        
    except ShopifyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {product_id} not found"
        )
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while fetching event {product_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch event from Shopify: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while fetching event {product_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.post("", response_model=ShababcoEvent, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    current_user: Annotated[User, Depends(get_current_active_superuser)]
) -> ShababcoEvent:
    """
    Create a new event in Shopify.
    
    Creates a product in Shopify with event-specific metafields.
    """
    try:
        product = await create_product(
            title=event_data.title,
            description=event_data.description,
            city=event_data.city,
            start_datetime=event_data.start_datetime,
            status=event_data.status
        )
        return ShababcoEvent(**product)
    except ShopifyValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while creating event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to create event in Shopify: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while creating event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
