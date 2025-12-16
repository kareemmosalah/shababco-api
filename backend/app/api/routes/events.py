"""
Admin events endpoints (CRUD).
Handles event management through Shopify integration.
"""
import logging
from typing import Optional, Annotated
from fastapi import APIRouter, HTTPException, Query, status, Depends

from app.schemas.event import EventCreate, ShababcoEvent, EventListResponse, CATEGORY_LABELS, STATUS_LABELS
from app.schemas.event_update import EventUpdate
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


@router.get("/metadata")
async def get_event_metadata():
    """
    Get event metadata including category and status labels.
    
    Returns mappings for categories and statuses to use in frontend dropdowns and displays.
    """
    return {
        "categories": [
            {"key": key, "label": label}
            for key, label in CATEGORY_LABELS.items()
        ],
        "statuses": [
            {"key": key, "label": label}
            for key, label in STATUS_LABELS.items()
        ]
    }

@router.get("", response_model=EventListResponse)
async def get_events(
    current_user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=50, description="Number of events to return per page (max 50)"),
    cursor: Optional[str] = Query(default=None, description="Pagination cursor for next page"),
    search: Optional[str] = Query(default=None, description="Search events by title, subtitle, description, and tags"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    status: Optional[str] = Query(default=None, description="Filter by status (active, draft, archived)")
):
    """
    List events with pagination, search, and filters.
    
    - **limit**: Number of events per page (default: 20, max: 50)
    - **cursor**: Pagination cursor from previous response
    - **search**: Multi-field search (title, subtitle, description, tags)
    - **category**: Filter by event category
    - **status**: Filter by status (active, draft, archived)
    """
    try:
        # Build Shopify query filter
        query_parts = ["product_type:event"]
        
        # Enhanced multi-field search
        if search:
            # Clean and prepare search term
            search_term = search.strip()
            
            # Build multi-field search query
            # Shopify syntax: (field1:term OR field2:term OR field3:term)
            # This searches across title, body (description), and tags
            search_fields = [
                f"title:*{search_term}*",           # Search in title
                f"body:*{search_term}*",            # Search in description (HTML content)
                f"tag:*{search_term}*",             # Search in tags
            ]
            
            # Combine with OR operator for broader results
            search_query = f"({' OR '.join(search_fields)})"
            query_parts.append(search_query)
        
        # Add status filter
        if status:
            # Map our status values to Shopify status values
            status_upper = status.upper()
            if status_upper in ["ACTIVE", "DRAFT", "ARCHIVED"]:
                query_parts.append(f"status:{status_upper}")
        
        # Note: Category filtering will be done post-fetch since it's stored in metafields
        # Shopify doesn't support filtering by metafields in the query
        
        query = " AND ".join(query_parts)
        
        result = await list_products(limit=limit, query=query, cursor=cursor)
        
        # Filter by category if specified (post-processing)
        events = result["products"]
        if category:
            events = [e for e in events if e.get("category") == category]
        
        return EventListResponse(
            events=events,
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
            subtitle=event_data.subtitle,
            category=event_data.category,
            tags=event_data.tags,
            cover_image=event_data.cover_image,
            gallery_images=event_data.gallery_images,
            venue_name=event_data.venue_name,
            city=event_data.city,
            address=event_data.address,
            country=event_data.country,
            location_link=event_data.location_link,
            start_datetime=event_data.start_datetime,
            end_datetime=event_data.end_datetime,
            organizer_name=event_data.organizer_name,
            seo_slug=event_data.seo_slug,
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


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_active_superuser)],
)
async def delete_event(
    product_id: str,
) -> None:
    """
    Delete an event (Shopify product) and all its tickets (variants).
    
    - **product_id**: Shopify product ID
    
    This will permanently delete the event and all associated tickets.
    """
    from app.integrations.shopify.products import delete_product
    
    try:
        # Delete the product (and all its variants)
        await delete_product(product_id)
        logger.info(f"Deleted event {product_id}")
        
    except ShopifyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {product_id} not found"
        )
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while deleting event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event in Shopify: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while deleting event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.patch(
    "/{product_id}",
    response_model=ShababcoEvent,
    dependencies=[Depends(get_current_active_superuser)],
)
async def update_event(
    product_id: str,
    event_data: EventUpdate,
) -> ShababcoEvent:
    """
    Update an event with partial data.
    Only provided fields will be updated.
    
    - **product_id**: Shopify product ID
    """
    from app.integrations.shopify.products import update_product
    
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = event_data.model_dump(exclude_none=True)
        
        # Update the product
        updated_product = await update_product(product_id, update_dict)
        
        logger.info(f"Updated event {product_id}")
        return ShababcoEvent(**updated_product)
        
    except ShopifyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {product_id} not found"
        )
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while updating event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while updating event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.patch(
    "/{product_id}/publish",
    response_model=ShababcoEvent,
    dependencies=[Depends(get_current_active_superuser)],
)
async def publish_event(
    product_id: str,
) -> ShababcoEvent:
    """
    Publish an event by changing its status to 'active'.
    
    Validates that:
    - Event exists
    - Event has at least one ticket
    - At least one ticket has inventory > 0
    
    - **product_id**: Shopify product ID
    """
    from app.integrations.shopify.products import update_product_status
    from app.integrations.shopify.variants import list_variants
    
    try:
        # 1. Validate event exists
        try:
            event = await fetch_product(product_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {product_id} not found"
            )
        
        # 2. Get all tickets for the event
        try:
            variants = await list_variants(product_id)
        except ShopifyAPIError as e:
            logger.error(f"Failed to fetch tickets for validation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to validate event tickets"
            )
        
        # 3. Validate at least one ticket exists
        if not variants or len(variants) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish event: Event must have at least one ticket"
            )
        
        # 4. Validate at least one ticket has inventory
        has_inventory = any(v.get("available", 0) > 0 for v in variants)
        if not has_inventory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish event: At least one ticket must have available inventory"
            )
        
        # 5. Update status to active
        try:
            await update_product_status(product_id, "active")
        except ShopifyAPIError as e:
            logger.error(f"Failed to update product status: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to publish event: {str(e)}"
            )
        
        # 6. Fetch and return updated event
        updated_event = await fetch_product(product_id)
        logger.info(f"Successfully published event {product_id}")
        return ShababcoEvent(**updated_event)
        
    except HTTPException:
        raise
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while publishing event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish event: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while publishing event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
