"""
Ticket update schemas for partial updates.
All fields are optional to allow updating only specific fields.
"""
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.ticket import TicketType


class TicketUpdate(BaseModel):
    """
    Schema for updating a ticket.
    All fields are optional - only provided fields will be updated.
    """
    ticket_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Ticket name/title")
    ticket_type: Optional[TicketType] = Field(None, description="Ticket type category")
    description: Optional[str] = Field(None, description="Ticket description (HTML)")
    features: Optional[list[str]] = Field(None, description="List of ticket features/benefits")
    is_visible: Optional[bool] = Field(None, description="Whether ticket is visible to customers")
    price: Optional[float] = Field(None, ge=0, description="Ticket price")
    compare_at_price: Optional[float] = Field(None, ge=0, description="Original price (for showing discount)")
    inventory_quantity: Optional[int] = Field(None, ge=0, description="Available ticket quantity")
    max_per_order: Optional[int] = Field(None, ge=1, le=100, description="Maximum tickets per order")
    
    class Config:
        json_schema_extra = {
            "example": {
                "price": 120.00,
                "compare_at_price": 150.00,
                "is_visible": True
            }
        }
