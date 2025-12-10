"""
Event schemas for Shopify integration.
Matches the ShababcoEvent TypeScript type.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


class EventBase(BaseModel):
    """Base event schema with common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    description: Optional[str] = Field(None, description="Event description (HTML supported)")
    city: Optional[str] = Field(None, description="Event city")
    start_datetime: Optional[str] = Field(None, description="Event start datetime in ISO format")


class EventCreate(EventBase):
    """Schema for creating a new event."""
    status: Literal["active", "draft", "archived"] = Field(
        default="draft",
        description="Event status"
    )


class ShababcoEvent(BaseModel):
    """
    Event response schema matching the TypeScript ShababcoEvent type.
    
    type ShababcoEvent = {
      shopify_product_id: string;
      title: string;
      description: string | null;
      status: "active" | "draft" | "archived" | "unlisted";
      city: string | null;
      start_datetime: string | null;
      total_tickets: number;
    };
    """
    shopify_product_id: str = Field(..., description="Shopify product ID")
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    status: Literal["active", "draft", "archived", "unlisted"] = Field(..., description="Event status")
    city: Optional[str] = Field(None, description="Event city")
    start_datetime: Optional[str] = Field(None, description="Event start datetime in ISO format")
    total_tickets: int = Field(..., description="Total available tickets")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shopify_product_id": "8234567890123",
                "title": "Summer Tech Meetup",
                "description": "A fantastic meetup for tech enthusiasts.",
                "status": "active",
                "city": "Cairo",
                "start_datetime": "2025-07-15T18:00:00Z",
                "total_tickets": 100
            }
        }


class EventListResponse(BaseModel):
    """Response schema for listing events."""
    events: list[ShababcoEvent] = Field(default_factory=list, description="List of events")
    has_next_page: bool = Field(default=False, description="Whether there are more pages")
    end_cursor: Optional[str] = Field(None, description="Cursor for next page")
