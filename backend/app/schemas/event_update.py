"""
Event update schemas for partial updates.
All fields are optional to allow updating only specific fields.
"""
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.event import EventCategory


class EventUpdate(BaseModel):
    """
    Schema for updating an event.
    All fields are optional - only provided fields will be updated.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Event title")
    subtitle: Optional[str] = Field(None, max_length=500, description="Event subtitle/tagline")
    description: Optional[str] = Field(None, description="Event description (HTML)")
    category: Optional[EventCategory] = Field(None, description="Event category")
    tags: Optional[list[str]] = Field(None, description="Event tags")
    cover_image: Optional[str] = Field(None, description="Cover image URL")
    gallery_images: Optional[list[str]] = Field(None, description="Gallery image URLs")
    venue_name: Optional[str] = Field(None, description="Venue name")
    city: Optional[str] = Field(None, description="City")
    address: Optional[str] = Field(None, description="Full address")
    country: Optional[str] = Field(None, description="Country")
    location_link: Optional[str] = Field(None, description="Google Maps link")
    start_datetime: Optional[str] = Field(None, description="Start date and time (ISO 8601)")
    end_datetime: Optional[str] = Field(None, description="End date and time (ISO 8601)")
    organizer_name: Optional[str] = Field(None, description="Organizer name")
    seo_slug: Optional[str] = Field(None, description="SEO-friendly URL slug")
    status: Optional[str] = Field(None, description="Event status (draft, active, archived)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Updated Event Title",
                "description": "<p>Updated description</p>",
                "start_datetime": "2025-07-15T20:00:00+02:00"
            }
        }
