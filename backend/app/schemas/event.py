"""
Event schemas for Shopify integration.
Matches the ShababcoEvent TypeScript type.
"""
from typing import Optional, Literal
from enum import Enum
from pydantic import BaseModel, Field


class EventCategory(str, Enum):
    """Event category keys (use CATEGORY_LABELS for display)."""
    MUSIC_CONCERTS = "music_concerts"
    NIGHTLIFE_PARTIES = "nightlife_parties"
    ART_CULTURE = "art_culture"
    COMEDY_SHOWS = "comedy_shows"
    SPORTS_FITNESS = "sports_fitness"
    FESTIVALS_FAIRS = "festivals_fairs"
    WORKSHOPS_EXPERIENCES = "workshops_experiences"
    ENTERTAINMENT_LIFESTYLE = "entertainment_lifestyle"
    FAMILY_KIDS = "family_kids"


# Category display labels for frontend
CATEGORY_LABELS = {
    "music_concerts": "Music & Concerts",
    "nightlife_parties": "Nightlife & Parties",
    "art_culture": "Art & Culture",
    "comedy_shows": "Comedy & Shows",
    "sports_fitness": "Sports & Fitness",
    "festivals_fairs": "Festivals & Fairs",
    "workshops_experiences": "Workshops & Experiences",
    "entertainment_lifestyle": "Entertainment & Lifestyle",
    "family_kids": "Family & Kids",
}


# Status display labels for frontend
STATUS_LABELS = {
    "active": "Published",
    "draft": "Draft",
    "archived": "Archived",
}


class EventBase(BaseModel):
    """Base event schema with common fields."""
    # Event Information
    title: str = Field(..., min_length=1, max_length=255, description="Event title")
    subtitle: Optional[str] = Field(None, max_length=500, description="Event subtitle/tagline")
    description: Optional[str] = Field(None, description="Event description (HTML supported)")
    category: Optional[EventCategory] = Field(
        None, 
        description="Event category key (e.g., 'music_concerts', 'nightlife_parties')"
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
    product_type: str = Field(default="event", description="Product type (always 'event' for events)")
    
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
    
    # Featured
    is_featured: bool = Field(default=False, description="Whether event is featured in hero carousel")
    
    # Popularity (optional, only included in popular endpoint)
    total_sold: int | None = Field(default=None, description="Total tickets sold (capacity - available)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "shopify_product_id": "8234567890123",
                "product_type": "event",
                "title": "Cairo Youth Culture Festival 2025",
                "subtitle": "Discover street culture, fashion, and live shows",
                "description": "<p>A fantastic festival for youth culture enthusiasts.</p>",
                "category": "music_concerts",
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
                "total_tickets": 100,
                "is_featured": False,
                "total_sold": 25
            }
        }


class PaginationInfo(BaseModel):
    """Pagination metadata."""
    current_page: int = Field(description="Current page number (1-indexed)")
    total_pages: int = Field(description="Total number of pages")
    total_count: int = Field(description="Total number of events")
    per_page: int = Field(description="Number of events per page")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")


class EventListResponse(BaseModel):
    """Response schema for listing events with offset-based pagination."""
    events: list[ShababcoEvent] = Field(default_factory=list, description="List of events")
    pagination: PaginationInfo = Field(description="Pagination metadata")
