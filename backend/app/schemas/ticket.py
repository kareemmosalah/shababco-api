"""
Ticket schemas for Shopify variant integration.
Tickets are Shopify product variants with extended properties in metafields.
"""
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class TicketType(str, Enum):
    """Ticket type options."""
    EARLY_BIRD = "early_bird"
    REGULAR = "regular"
    VIP = "vip"
    STUDENT = "student"
    GROUP = "group"


class TicketBase(BaseModel):
    """Base ticket schema with common fields."""
    ticket_name: str = Field(..., min_length=1, max_length=255, description="Ticket name/title")
    ticket_type: TicketType = Field(..., description="Ticket type category")
    description: Optional[str] = Field(None, description="Ticket description (HTML supported)")
    features: Optional[list[str]] = Field(default=None, description="List of ticket features/benefits")
    is_visible: bool = Field(default=True, description="Whether ticket is visible to customers")
    price: float = Field(..., ge=0, description="Ticket price")
    compare_at_price: Optional[float] = Field(None, ge=0, description="Original price (for showing discount)")
    inventory_quantity: int = Field(..., ge=0, description="Available ticket quantity")
    max_per_order: int = Field(default=10, ge=1, le=100, description="Maximum tickets per order")


class TicketCreate(TicketBase):
    """Schema for creating a new ticket (variant)."""
    shopify_product_id: str = Field(..., description="Product ID to add ticket to")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shopify_product_id": "8234567890123",
                "ticket_name": "Early Bird",
                "ticket_type": "early_bird",
                "description": "<p>Get early access to the event with exclusive perks</p>",
                "features": [
                    "Early access (30 minutes before general admission)",
                    "Free welcome drink",
                    "Priority seating"
                ],
                "is_visible": True,
                "price": 100.00,
                "compare_at_price": 150.00,
                "inventory_quantity": 100,
                "max_per_order": 4
            }
        }


class TicketResponse(TicketBase):
    """Schema for ticket response."""
    shopify_variant_id: str = Field(..., description="Shopify variant ID")
    sold_count: int = Field(default=0, description="Number of tickets sold")
    available_quantity: int = Field(default=0, description="Number of tickets available")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shopify_variant_id": "8234567890124",
                "ticket_name": "Early Bird",
                "ticket_type": "early_bird",
                "description": "<p>Get early access to the event with exclusive perks</p>",
                "features": [
                    "Early access (30 minutes before general admission)",
                    "Free welcome drink",
                    "Priority seating"
                ],
                "is_visible": True,
                "price": 100.00,
                "compare_at_price": 150.00,
                "inventory_quantity": 100,
                "max_per_order": 4,
                "sold_count": 0,
                "available_quantity": 100
            }
        }


class TicketListItem(BaseModel):
    """Simplified ticket schema for list views (table display)."""
    shopify_variant_id: str
    ticket_name: str
    ticket_type: TicketType
    price: float
    capacity: int
    sold: int
    revenue: float
    is_visible: bool = Field(default=True, description="Whether ticket is visible to customers")
    status: str  # "active", "sold_out", "hidden"
    
    class Config:
        json_schema_extra = {
            "example": {
                "shopify_variant_id": "45970216779947",
                "ticket_name": "Early Bird",
                "ticket_type": "early_bird",
                "price": 100.00,
                "capacity": 200,
                "sold": 50,
                "revenue": 5000.00,
                "is_visible": True,
                "status": "active"
            }
        }
