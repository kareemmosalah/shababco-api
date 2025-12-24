"""
Ticket API routes for managing event tickets (Shopify variants).
"""
import logging
from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Depends

from app.api.deps import CurrentUser, get_current_active_superuser
from app.models import User
from app.schemas.ticket import TicketCreate, TicketResponse, TicketListItem
from app.schemas.ticket_update import TicketUpdate
from app.integrations.shopify import fetch_product, ShopifyAPIError, ShopifyNotFoundError
from app.integrations.shopify.variants import create_variant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["Tickets"])


@router.post("/{product_id}/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    product_id: str,
    ticket: TicketCreate,
    current_user: Annotated[User, Depends(get_current_active_superuser)]
):
    """
    Create a new ticket (variant) for an event.
    
    - **product_id**: Shopify product ID
    - **ticket**: Ticket data including name, type, price, inventory, etc.
    
    Tickets are Shopify product variants with extended properties stored in metafields.
    """
    try:
        # Validate product exists
        try:
            product = await fetch_product(product_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {product_id} not found"
            )
        
        # Validate product_id matches
        if ticket.shopify_product_id != product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product ID in request body must match URL parameter"
            )
        
        # Create variant with metafields
        variant_data = await create_variant(
            product_id=product_id,
            ticket_name=ticket.ticket_name,
            ticket_type=ticket.ticket_type.value,
            price=ticket.price,
            inventory_quantity=ticket.inventory_quantity,
            description=ticket.description,
            features=ticket.features,
            is_visible=ticket.is_visible,
            compare_at_price=ticket.compare_at_price,
            max_per_order=ticket.max_per_order
        )
        
        logger.info(f"Created ticket '{ticket.ticket_name}' for product {product_id}")
        
        return TicketResponse(**variant_data)
        
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while creating ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to create ticket in Shopify: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while creating ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.delete(
    "/{product_id}/tickets/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_active_superuser)],
)
async def delete_ticket(
    product_id: str,
    variant_id: str,
) -> None:
    """
    Delete a ticket (variant).
    
    Deletion rules:
    - If ticket has NO sales: Can delete
    - If ticket has sales: CANNOT delete (must hide instead)
    
    - **product_id**: Shopify product ID
    - **variant_id**: Shopify variant ID
    """
    from app.integrations.shopify.variants import delete_variant, get_variant
    
    try:
        # Validate product exists
        try:
            product = await fetch_product(product_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {product_id} not found"
            )
        
        # Get ticket to check sales
        try:
            ticket = await get_variant(variant_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        sold_count = ticket.get('sold', 0)
        
        # Prevent deletion if ticket has sales
        if sold_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete ticket with {sold_count} sales. "
                       f"Hide it instead by setting visibility to false."
            )
        
        # Delete the variant
        await delete_variant(product_id, variant_id)
        
        logger.info(f"Deleted ticket {variant_id} from product {product_id}")
        
    except HTTPException:
        # Re-raise HTTP exceptions (including validation errors)
        raise
    except ShopifyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while deleting ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete ticket: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while deleting ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.patch(
    "/{product_id}/tickets/{variant_id}",
    response_model=TicketResponse,
    dependencies=[Depends(get_current_active_superuser)],
)
async def update_ticket(
    product_id: str,
    variant_id: str,
    ticket_data: TicketUpdate,
) -> TicketResponse:
    """
    Update a ticket with partial data.
    
    Field locking rules:
    - If ticket has NO sales: All fields editable
    - If ticket has sales: Only price, inventory (increase), and visibility editable
    
    Locked fields after sales:
    - ticket_name, ticket_type, description, features, compare_at_price, max_per_order
    
    - **product_id**: Shopify product ID
    - **variant_id**: Shopify variant ID
    """
    from app.integrations.shopify.variants import update_variant, get_variant
    
    try:
        # Validate product exists
        try:
            product = await fetch_product(product_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {product_id} not found"
            )
        
        # Get current ticket to check sales
        try:
            current_ticket = await get_variant(variant_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )
        
        sold_count = current_ticket.get('sold', 0)
        has_sales = sold_count > 0
        
        # Convert Pydantic model to dict, excluding None values
        update_dict = ticket_data.model_dump(exclude_none=True)
        
        # Validate field locking if ticket has sales
        if has_sales:
            # Define locked fields (cannot be changed after sales)
            locked_fields = {
                'ticket_name': 'Ticket name',
                'ticket_type': 'Ticket type',
                'description': 'Description',
                'features': 'Features',
                'compare_at_price': 'Compare-at price',
                'max_per_order': 'Max per order'
            }
            
            # Check if trying to edit locked fields
            for field, display_name in locked_fields.items():
                if field in update_dict:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot edit {display_name} after sales. "
                               f"This ticket has {sold_count} confirmed buyers. "
                               f"Create a new ticket instead."
                    )
            
            # Validate inventory changes
            if 'inventory_quantity' in update_dict:
                new_inventory = update_dict['inventory_quantity']
                if new_inventory < sold_count:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot set inventory below sold count. "
                               f"Sold: {sold_count}, Attempted: {new_inventory}"
                    )
        
        # Update the variant
        updated_variant = await update_variant(product_id, variant_id, update_dict)
        
        # Invalidate caches so UI shows updated data immediately
        from app.core.cache import invalidate_event_caches, invalidate_ticket_caches
        invalidate_event_caches(product_id)
        invalidate_ticket_caches(event_id=product_id)
        
        logger.info(f"Updated ticket {variant_id} and invalidated caches")
        return TicketResponse(**updated_variant)
        
    except HTTPException:
        # Re-raise HTTP exceptions (including validation errors)
        raise
    except ShopifyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while updating ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update ticket: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while updating ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/{product_id}/tickets-view",
    response_model=list[TicketListItem],
)
async def get_tickets_view(
    product_id: str,
    current_user: CurrentUser,
) -> list[TicketListItem]:
    """
    Get simplified tickets view for displaying in a table.
    
    Returns a list of tickets with summary information:
    - Ticket name
    - Price
    - Capacity (total inventory)
    - Sold count
    - Revenue (sold × price)
    - Status (active, sold_out, hidden)
    
    For full ticket details, use GET /events/{product_id}/tickets instead.
    
    - **product_id**: Shopify product ID
    """
    from app.integrations.shopify.variants import list_variants
    from app.schemas.ticket import TicketListItem
    from app.core.cache import get_cached_event_tickets, cache_event_tickets
    
    try:
        # Check cache first
        cached_tickets = get_cached_event_tickets(product_id)
        if cached_tickets:
            logger.info(f"✅ Cache HIT for tickets of event {product_id}")
            return [TicketListItem(**ticket) for ticket in cached_tickets]
        
        logger.info(f"⚠️ Cache MISS for tickets of event {product_id}")
        
        # Validate product exists
        try:
            product = await fetch_product(product_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {product_id} not found"
            )
        
        # Get all variants from Shopify
        variants = await list_variants(product_id)
        
        # Cache tickets for 10 minutes
        cache_event_tickets(product_id, variants, ttl=600)
        logger.info(f"💾 Cached {len(variants)} tickets for event {product_id}")
        
        # Convert to TicketListItem
        tickets = [TicketListItem(**variant) for variant in variants]
        
        logger.info(f"Retrieved {len(tickets)} tickets for product {product_id}")
        return tickets
        
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while listing tickets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tickets from Shopify: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error while listing tickets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
