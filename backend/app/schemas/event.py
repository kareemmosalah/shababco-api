"""
Event schemas for Shopify integration.
Matches the ShababcoEvent TypeScript type.
"""
from typing import Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field


class EventCategory(str, Enum):
    """Event category options."""
    MUSIC_CONCERTS = "Music & Concerts"
    NIGHTLIFE_PARTIES = "Nightlife & Parties"
    ART_CULTURE = "Art & Culture"
    COMEDY_SHOWS = "Comedy & Shows"
    SPORTS_FITNESS = "Sports & Fitness"
    FESTIVALS_FAIRS = "Festivals & Fairs"
    WORKSHOPS_EXPERIENCES = "Workshops & Experiences"
    ENTERTAINMENT_LIFESTYLE = "Entertainment & Lifestyle"
    FAMILY_KIDS = "Family & Kids"


class EventBase(BaseModel):
    """Base event schema with common fields."""
    # Event Information
    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    subtitle: Optional[str] = Field(None, max_length=500, description="Event subtitle/tagline")
    description: Optional[str] = Field(None, description="Event description (HTML supported)")
    category: Optional[EventCategory] = Field(
        None, 
        description="Event category. Options: Music & Concerts, Nightlife & Parties, Art & Culture, Comedy & Shows, Sports & Fitness, Festivals & Fairs, Workshops & Experiences, Entertainment & Lifestyle, Family & Kids"
    )
    tags: Optional[list[str]] = Field(default=None, description="Event tags")
    cover_image: Optional[str] = Field(None, description="Cover image URL")
    gallery_images: Optional[list[str]] = Field(default=None, description="Gallery image URLs")
    
    # Location & Time
    venue_name: Optional[str] = Field(None, max_length=255, description="Venue name")
    city: Optional[str] = Field(None, max_length=100, description="Event city")
    address: Optional[str] = Field(None, max_length=500, description="Full address")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    location_link: Optional[str] = Field(None, description="Google Maps or location URL")
    start_datetime: Optional[str] = Field(None, description="Event start datetime in ISO format")
    end_datetime: Optional[str] = Field(None, description="Event end datetime in ISO format")
    
    # Organizer
    organizer_name: Optional[str] = Field(None, max_length=255, description="Organizer name")
    
    # SEO
    seo_slug: Optional[str] = Field(None, max_length=255, description="SEO slug (URL handle)")


class EventCreate(EventBase):
    """Schema for creating a new event."""
    status: Literal["active", "draft", "archived"] = Field(
        default="draft",
        description="Event status"
    )


class ShababcoEvent(BaseModel):
    """
    Event response schema matching the enhanced event structure.
    """
    shopify_product_id: str = Field(..., description="Shopify product ID")
    
    # Event Information
    title: str = Field(..., description="Event title")
    subtitle: Optional[str] = Field(None, description="Event subtitle/tagline")
    description: Optional[str] = Field(None, description="Event description")
    category: Optional[str] = Field(None, description="Event category")  # String to handle legacy data
    tags: Optional[list[str]] = Field(default=None, description="Event tags")
    cover_image: Optional[str] = Field(None, description="Cover image URL")
    gallery_images: Optional[list[str]] = Field(default=None, description="Gallery image URLs")
    
    # Location & Time
    venue_name: Optional[str] = Field(None, description="Venue name")
    city: Optional[str] = Field(None, description="Event city")
    address: Optional[str] = Field(None, description="Full address")
    country: Optional[str] = Field(None, description="Country")
    location_link: Optional[str] = Field(None, description="Google Maps or location URL")
    start_datetime: Optional[str] = Field(None, description="Event start datetime in ISO format")
    end_datetime: Optional[str] = Field(None, description="Event end datetime in ISO format")
    
    # Organizer
    organizer_name: Optional[str] = Field(None, description="Organizer name")
    
    # SEO
    seo_slug: Optional[str] = Field(None, description="SEO slug (URL handle)")
    
    # Status & Inventory
    status: Literal["active", "draft", "archived", "unlisted"] = Field(..., description="Event status")
    total_tickets: int = Field(..., description="Total available tickets")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shopify_product_id": "8234567890123",
                "title": "Cairo Youth Culture Festival 2025",
                "subtitle": "Discover street culture, fashion, and live shows",
                "description": "<p>A fantastic festival for youth culture enthusiasts.</p>",
                "category": "Music & Concerts",
                "tags": ["festival", "youth", "culture", "cairo"],
                "cover_image": "https://example.com/cover.jpg",
                "gallery_images": ["https://example.com/gallery1.jpg", "https://example.com/gallery2.jpg"],
                "venue_name": "Cairo Stadium",
                "city": "Cairo",
                "address": "123 Stadium St, Nasr City",
                "country": "Egypt",
                "location_link": "https://maps.google.com/?q=Cairo+Stadium",
                "start_datetime": "2025-09-10T16:00:00Z",
                "end_datetime": "2025-09-10T23:00:00Z",
                "organizer_name": "Shababco Events",
                "seo_slug": "cairo-youth-culture-festival-2025",
                "status": "active",
                "total_tickets": 100
            }
        }


class EventListResponse(BaseModel):
    """Response schema for listing events."""
    events: list[ShababcoEvent] = Field(default_factory=list, description="List of events")
    has_next_page: bool = Field(default=False, description="Whether there are more pages")
    end_cursor: Optional[str] = Field(None, description="Cursor for next page")
