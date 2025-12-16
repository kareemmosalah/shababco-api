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
    Delete a ticket (Shopify variant).
    
    - **product_id**: Shopify product ID
    - **variant_id**: Shopify variant ID to delete
    """
    from app.integrations.shopify.variants import delete_variant
    
    try:
        # Delete the variant
        await delete_variant(product_id, variant_id)
        logger.info(f"Deleted ticket variant {variant_id} from product {product_id}")
        
    except ShopifyAPIError as e:
        logger.error(f"Shopify API error while deleting ticket: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete ticket in Shopify: {str(e)}"
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
    Only provided fields will be updated.
    
    - **product_id**: Shopify product ID
    - **variant_id**: Shopify variant ID
    """
    from app.integrations.shopify.variants import update_variant
    
    try:
        # Validate product exists
        try:
            product = await fetch_product(product_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {product_id} not found"
            )
        
        # Convert Pydantic model to dict, excluding None values
        update_dict = ticket_data.model_dump(exclude_none=True)
        
        # Update the variant
        updated_variant = await update_variant(product_id, variant_id, update_dict)
        
        logger.info(f"Updated ticket {variant_id} for product {product_id}")
        return TicketResponse(**updated_variant)
        
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
    
    try:
        # Validate product exists
        try:
            product = await fetch_product(product_id)
        except ShopifyNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event with ID {product_id} not found"
            )
        
        # Get all variants
        variants = await list_variants(product_id)
        
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
