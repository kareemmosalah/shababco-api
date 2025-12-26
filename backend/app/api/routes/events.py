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
from app.core.cache import cache_get, cache_set, cache_delete, invalidate_event_caches

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


@router.get("/popular", response_model=list[ShababcoEvent])
async def get_popular_events(
    limit: int = Query(default=10, ge=1, le=50, description="Number of popular events to return")
):
    """
    Get most popular events based on tickets sold.
    
    Returns top events sorted by total tickets sold (descending).
    Public endpoint - no authentication required.
    
    Sold calculation: capacity (from metafield) - current inventory
    
    - **limit**: Number of events to return (default: 10, max: 50)
    """
    from app.integrations.shopify.variants import list_variants
    
    try:
        # Check cache first
        cache_key = f"events:popular:limit={limit}"
        cached_response = cache_get(cache_key)
        if cached_response:
            logger.info(f"✅ Cache HIT for popular events")
            return cached_response
        
        logger.info(f"⚠️ Cache MISS for popular events - fetching from Shopify")
        
        # Fetch all active events
        all_events = []
        cursor = None
        
        while True:
            result = await list_products(limit=50, query="product_type:event AND status:active", cursor=cursor)
            all_events.extend(result["products"])
            
            if not result.get("has_next_page", False):
                break
            
            cursor = result.get("end_cursor")
            
            # Safety limit
            if len(all_events) >= 500:
                break
        
        # Calculate sold tickets for each event
        events_with_sales = []
        
        for event in all_events:
            product_id = event.get("shopify_product_id")
            
            try:
                # Get variants (tickets) for this event
                variants = await list_variants(product_id)
                
                # Calculate total sold tickets using the correct formula:
                # sold = capacity (from metafield) - available (current inventory)
                # This matches the tickets endpoint calculation
                total_sold = 0
                for variant in variants:
                    # Get capacity from metafield
                    capacity = variant.get("capacity", 0)
                    available = variant.get("available", 0)
                    
                    # Calculate sold: capacity - available
                    sold = max(0, capacity - available)
                    total_sold += sold
                
                # Add sold count to event
                event["total_sold"] = total_sold
                events_with_sales.append(event)
                
            except Exception as e:
                logger.warning(f"Failed to get sales for event {product_id}: {str(e)}")
                # Include event with 0 sales if we can't fetch variants
                event["total_sold"] = 0
                events_with_sales.append(event)
        
        # Sort by total sold (descending)
        events_with_sales.sort(key=lambda e: e.get("total_sold", 0), reverse=True)
        
        # Get top N events
        popular_events = events_with_sales[:limit]
        
        # Cache for 10 minutes
        cache_set(cache_key, popular_events, ttl=600)
        logger.info(f"💾 Cached popular events for 10 minutes")
        
        return popular_events
        
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while fetching popular events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch popular events: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while fetching popular events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("", response_model=EventListResponse)
async def get_events(
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=20, ge=1, le=50, description="Number of events per page"),
    search: Optional[str] = Query(default=None, description="Search events by title, subtitle, description, and tags"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    status: Optional[str] = Query(default=None, description="Filter by status (active, draft, archived)"),
    featured: Optional[bool] = Query(default=None, description="Filter by featured status (true for featured only)")
):
    """
    List events with offset-based pagination, search, and filters.
    
    - **page**: Page number (default: 1)
    - **limit**: Number of events per page (default: 20, max: 50)
    - **search**: Multi-field search (title, subtitle, description, tags)
    - **category**: Filter by event category
    - **status**: Filter by status (active, draft, archived)
    
    Returns paginated results with page numbers, total count, and previous/next indicators.
    """
    try:
        # Generate cache key based on query parameters
        cache_key = f"events:list:page={page}:limit={limit}:search={search}:category={category}:status={status}:featured={featured}"
        
        # Try to get from cache first
        cached_response = cache_get(cache_key)
        if cached_response:
            logger.info(f"✅ Cache HIT for events list (page {page})")
            return cached_response
        
        logger.info(f"⚠️ Cache MISS for events list (page {page}) - fetching from Shopify")
        
        # Build Shopify query filter
        query_parts = ["product_type:event"]
        
        # Enhanced multi-field search
        if search:
            search_term = search.strip()
            search_fields = [
                f"title:*{search_term}*",
                f"body:*{search_term}*",
                f"tag:*{search_term}*",
            ]
            search_query = f"({' OR '.join(search_fields)})"
            query_parts.append(search_query)
        
        # Add status filter
        if status:
            status_upper = status.upper()
            if status_upper in ["ACTIVE", "DRAFT", "ARCHIVED"]:
                query_parts.append(f"status:{status_upper}")
        
        query = " AND ".join(query_parts)
        
        # Fetch all matching events using cursor pagination
        # Optimized: fetch in batches and cache
        all_events = []
        cursor = None
        
        # Fetch in batches of 50 (max Shopify allows)
        while True:
            result = await list_products(limit=50, query=query, cursor=cursor)
            batch_events = result["products"]
            
            # Filter by category if specified
            if category:
                batch_events = [e for e in batch_events if e.get("category") == category]
            
            # Filter by featured if specified
            if featured is not None:
                batch_events = [e for e in batch_events if e.get("is_featured") == featured]
            
            all_events.extend(batch_events)
            
            # Check if there are more pages
            if not result.get("has_next_page", False):
                break
            
            cursor = result.get("end_cursor")
            
            # Safety limit: max 500 events
            if len(all_events) >= 500:
                break
        
        # Sort events: featured first, then by date
        all_events.sort(key=lambda e: (not e.get("is_featured", False), e.get("start_datetime") or ""))
        
        # Calculate pagination
        total_count = len(all_events)
        total_pages = max(1, (total_count + limit - 1) // limit)
        
        # Validate and adjust page number
        if page > total_pages and total_count > 0:
            page = total_pages
        
        # Calculate offset
        offset = (page - 1) * limit
        
        # Slice events for current page
        paginated_events = all_events[offset:offset + limit]
        
        # Build pagination metadata
        from app.schemas.event import PaginationInfo
        pagination = PaginationInfo(
            current_page=page,
            total_pages=total_pages,
            total_count=total_count,
            per_page=limit,
            has_next=page < total_pages,
            has_previous=page > 1
        )
        
        # Cache the response for 5 minutes
        cache_set(cache_key, {"events": paginated_events, "pagination": pagination.model_dump()}, ttl=300)
        logger.info(f"💾 Cached events list for 5 minutes")
        
        # Debug: Check what we have
        logger.info(f"🔍 DEBUG: paginated_events has {len(paginated_events)} events")
        if paginated_events:
            logger.info(f"🔍 DEBUG: First event ID: {paginated_events[0].get('id')}, Title: {paginated_events[0].get('title')}")
        
        # IMPORTANT: Also cache each individual event's full details AND tickets
        # This ensures clicking an event loads everything from cache, not Shopify
        from app.core.cache import cache_full_event, cache_event_tickets
        from app.integrations.shopify.variants import list_variants
        
        cached_events_count = 0
        cached_tickets_count = 0
        
        for event in paginated_events:
            # Cache only the event itself (tickets cached on-demand when viewing event)
            event_id = event.get("shopify_product_id")
            if event_id:
                cache_full_event(event_id, event, ttl=600)
                cached_events_count += 1
        
        logger.info(f"💾 Dashboard cached {cached_events_count} events (tickets cached on-demand)")
        
        return EventListResponse(
            events=paginated_events,
            pagination=pagination
        )
        
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while listing events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch events from Shopify: {str(e)}")
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
        # Check cache first (full event with tickets)
        from app.core.cache import get_cached_full_event, cache_full_event
        
        cached_event = get_cached_full_event(product_id)
        if cached_event:
            logger.info(f"✅ Cache HIT for event {product_id}")
            return ShababcoEvent(**cached_event)
        
        logger.info(f"⚠️ Cache MISS for event {product_id} - fetching from Shopify")
        
        # Fetch from Shopify
        event = await fetch_product(product_id)
        
        # Cache for 10 minutes
        cache_full_event(product_id, event, ttl=600)
        logger.info(f"💾 Cached event {product_id} for 10 minutes")
        
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
        # Invalidate events list cache
        invalidate_event_caches()
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
    from app.integrations.shopify.variants import list_variants
    
    try:
        # 1. Check if event has sold tickets
        try:
            variants = await list_variants(product_id)
            total_sold = sum(v.get("sold", 0) for v in variants)
            
            if total_sold > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot delete event with {total_sold} sold tickets. "
                           f"Please archive the event instead or contact support."
                )
        except HTTPException:
            raise  # Re-raise validation errors
        except Exception as e:
            logger.warning(f"Could not validate tickets for deletion: {e}")
            # Continue with deletion if we can't fetch tickets
        
        # 2. Delete the product (and all its variants)
        await delete_product(product_id)
        
        # 3. Invalidate caches
        invalidate_event_caches()
        
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
    
    Status transition rules:
    - draft → active: Allowed (via /publish endpoint)
    - active → archived: Allowed
    - archived → active: Allowed (via /publish endpoint)
    - active → draft: FORBIDDEN (must archive instead)
    - archived → draft: FORBIDDEN (must publish instead)
    - draft → archived: FORBIDDEN (must publish first)
    
    - **product_id**: Shopify product ID
    """
    from app.integrations.shopify.products import update_product
    from app.integrations.shopify.variants import list_variants
    
    try:
        # Fetch current event to check status transitions
        try:
            current_event = await fetch_product(product_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {product_id} not found"
            )
        
        current_status = current_event.get("status", "").lower()
        
        # Convert Pydantic model to dict, excluding None values
        update_dict = event_data.model_dump(exclude_none=True)
        
        # Validate status transitions if status is being changed
        if "status" in update_dict:
            new_status = update_dict["status"].lower()
            
            # Define forbidden transitions
            forbidden_transitions = {
                ("active", "draft"): "Cannot unpublish active event. Use archive instead.",
                ("archived", "draft"): "Cannot change archived event to draft. Use publish endpoint to make it active.",
                ("draft", "archived"): "Cannot archive draft event. Publish it first.",
            }
            
            # Check if transition is forbidden
            transition = (current_status, new_status)
            if transition in forbidden_transitions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=forbidden_transitions[transition]
                )
            
            # If changing to active status, validate tickets exist
            if new_status == "active" and current_status != "active":
                try:
                    variants = await list_variants(product_id)
                    
                    # Check if event has tickets
                    if not variants or len(variants) == 0:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot publish event: Event must have at least one ticket"
                        )
                    
                    # Check if at least one ticket has inventory
                    has_inventory = any(v.get("available", 0) > 0 for v in variants)
                    if not has_inventory:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot publish event: At least one ticket must have available inventory"
                        )
                except ShopifyAPIError as e:
                    logger.error(f"Failed to validate tickets: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to validate event tickets"
                    )
        
        # Perform the update
        updated_product = await update_product(product_id, update_dict)
        
        logger.info(f"Successfully updated event {product_id}")
        # Invalidate events list cache
        invalidate_event_caches()
        return ShababcoEvent(**updated_product)
        
    except HTTPException:
        # Re-raise HTTP exceptions (including validation errors)
        raise
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
        # Invalidate events list cache
        invalidate_event_caches()
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


@router.patch(
    "/{product_id}/featured",
    response_model=ShababcoEvent,
    dependencies=[Depends(get_current_active_superuser)],
)
async def toggle_featured(
    product_id: str,
    is_featured: bool = Query(..., description="Set event as featured")
) -> ShababcoEvent:
    """
    Toggle featured status for an event.
    
    Featured events appear in the hero carousel on the homepage.
    
    **Validation:**
    - Event must be published (status=active) to be featured
    - Cannot feature draft or archived events
    
    - **product_id**: Shopify product ID
    - **is_featured**: True to feature the event, False to unfeature
    """
    from app.integrations.shopify.featured import update_is_featured
    
    try:
        # 1. Validate event exists
        try:
            event = await fetch_product(product_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {product_id} not found"
            )
        
        # 2. Validate event is published before featuring
        if is_featured:
            event_status = event.get("status", "").lower()
            if event_status != "active":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot feature unpublished event. Event status is '{event_status}'. "
                           f"Please publish the event first before featuring it."
                )
        
        # 3. Update is_featured metafield
        try:
            await update_is_featured(product_id, is_featured)
        except ShopifyAPIError as e:
            logger.error(f"Failed to update is_featured: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update featured status: {str(e)}"
            )
        
        # 4. Fetch and return updated event
        updated_event = await fetch_product(product_id)
        logger.info(f"Successfully set is_featured={is_featured} for event {product_id}")
        
        # Invalidate events list cache
        invalidate_event_caches()
        
        return ShababcoEvent(**updated_event)
        
    except HTTPException:
        raise
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while updating featured status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update featured status: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while updating featured status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
