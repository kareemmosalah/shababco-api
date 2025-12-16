#!/usr/bin/env python3
"""
Generate 30 draft events for testing.
Run: python3 generate_test_events.py
"""
import requests
import json
from datetime import datetime, timedelta
import random

API_BASE_URL = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjY1NzQ1MzcsInN1YiI6IjljM2M2MTZmLTdmNTktNDcxNi1hYmM3LTMzMDYzNzYzMDViMiJ9.0Od5tGTrKOuEf7F4WgibSgoZyeHxpC5g2KXYomMYSg0"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Event data templates
EVENTS = [
    # Music & Concerts
    {
        "title": "Cairo Jazz Festival 2025",
        "subtitle": "Three nights of world-class jazz performances",
        "description": "<p>Experience the best of international and local jazz artists in Cairo's premier music venue.</p>",
        "category": "music_concerts",
        "tags": ["jazz", "music", "festival", "cairo"],
        "venue_name": "Cairo Opera House",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Cairo Jazz Society"
    },
    {
        "title": "Mahraganat Night Live",
        "subtitle": "Egypt's biggest Mahraganat stars",
        "description": "<p>Dance the night away with Egypt's hottest Mahraganat DJs and performers.</p>",
        "category": "music_concerts",
        "tags": ["mahraganat", "edm", "party", "cairo"],
        "venue_name": "New Cairo Arena",
        "city": "New Cairo",
        "country": "Egypt",
        "organizer_name": "Shababco Events"
    },
    {
        "title": "Amr Diab Live in Alexandria",
        "subtitle": "The legend returns to his hometown",
        "description": "<p>Amr Diab performs his greatest hits in an unforgettable concert.</p>",
        "category": "music_concerts",
        "tags": ["amr-diab", "arabic-music", "concert", "alexandria"],
        "venue_name": "Bibliotheca Alexandrina",
        "city": "Alexandria",
        "country": "Egypt",
        "organizer_name": "Live Nation Egypt"
    },
    {
        "title": "Underground Rock Festival",
        "subtitle": "Egypt's alternative music scene",
        "description": "<p>Featuring the best underground rock and indie bands from across Egypt.</p>",
        "category": "music_concerts",
        "tags": ["rock", "indie", "underground", "cairo"],
        "venue_name": "The Tap East",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Rock Egypt"
    },
    
    # Nightlife & Parties
    {
        "title": "Sahel Summer Opening Party",
        "subtitle": "Kick off the summer season in style",
        "description": "<p>The biggest beach party of the year with international DJs.</p>",
        "category": "nightlife_parties",
        "tags": ["beach", "party", "sahel", "summer"],
        "venue_name": "Hacienda Bay Beach Club",
        "city": "Sahel",
        "country": "Egypt",
        "organizer_name": "Sahel Events"
    },
    {
        "title": "Rooftop Sunset Sessions",
        "subtitle": "Chill vibes and city views",
        "description": "<p>Weekly sunset party with house music and stunning Cairo skyline views.</p>",
        "category": "nightlife_parties",
        "tags": ["rooftop", "sunset", "house-music", "cairo"],
        "venue_name": "The Roof Zamalek",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Shababco Events"
    },
    {
        "title": "Neon Nights - Glow Party",
        "subtitle": "Egypt's biggest glow-in-the-dark party",
        "description": "<p>Dress in white and glow under UV lights with the best EDM DJs.</p>",
        "category": "nightlife_parties",
        "tags": ["glow", "edm", "party", "cairo"],
        "venue_name": "Cairo Festival City",
        "city": "New Cairo",
        "country": "Egypt",
        "organizer_name": "Neon Events"
    },
    
    # Art & Culture
    {
        "title": "Contemporary Egyptian Art Exhibition",
        "subtitle": "Showcasing modern Egyptian artists",
        "description": "<p>A curated collection of contemporary art from Egypt's rising stars.</p>",
        "category": "art_culture",
        "tags": ["art", "exhibition", "contemporary", "cairo"],
        "venue_name": "Townhouse Gallery",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Townhouse Gallery"
    },
    {
        "title": "Cairo International Film Festival",
        "subtitle": "Celebrating 45 years of cinema",
        "description": "<p>The oldest film festival in the Middle East returns with world premieres.</p>",
        "category": "art_culture",
        "tags": ["film", "cinema", "festival", "cairo"],
        "venue_name": "Cairo Opera House",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "CIFF"
    },
    {
        "title": "Street Art Walking Tour",
        "subtitle": "Discover Cairo's urban art scene",
        "description": "<p>Guided tour through Cairo's most vibrant street art neighborhoods.</p>",
        "category": "art_culture",
        "tags": ["street-art", "tour", "culture", "cairo"],
        "venue_name": "Downtown Cairo",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Cairo Street Art"
    },
    {
        "title": "Pharaonic Heritage Night",
        "subtitle": "Ancient Egypt comes alive",
        "description": "<p>Experience ancient Egyptian culture through music, dance, and storytelling.</p>",
        "category": "art_culture",
        "tags": ["heritage", "pharaonic", "culture", "giza"],
        "venue_name": "Giza Pyramids",
        "city": "Giza",
        "country": "Egypt",
        "organizer_name": "Heritage Egypt"
    },
    
    # Comedy & Shows
    {
        "title": "Ahmed Helmy Stand-Up Special",
        "subtitle": "Egypt's comedy king returns",
        "description": "<p>An evening of laughter with one of Egypt's most beloved comedians.</p>",
        "category": "comedy_shows",
        "tags": ["comedy", "stand-up", "ahmed-helmy", "cairo"],
        "venue_name": "Cairo Stadium Indoor Hall",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Comedy Egypt"
    },
    {
        "title": "Open Mic Comedy Night",
        "subtitle": "Discover Egypt's next comedy stars",
        "description": "<p>Weekly open mic featuring up-and-coming Egyptian comedians.</p>",
        "category": "comedy_shows",
        "tags": ["comedy", "open-mic", "stand-up", "cairo"],
        "venue_name": "The Tap Maadi",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Shababco Events"
    },
    {
        "title": "Magic & Illusion Show",
        "subtitle": "Mind-bending magic from international illusionists",
        "description": "<p>A spectacular evening of magic, illusions, and wonder for all ages.</p>",
        "category": "comedy_shows",
        "tags": ["magic", "illusion", "show", "cairo"],
        "venue_name": "Cairo Opera House",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Magic Egypt"
    },
    
    # Sports & Fitness
    {
        "title": "Cairo Marathon 2025",
        "subtitle": "Run through history",
        "description": "<p>Egypt's premier marathon event with routes passing iconic landmarks.</p>",
        "category": "sports_fitness",
        "tags": ["marathon", "running", "sports", "cairo"],
        "venue_name": "Tahrir Square",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Cairo Runners"
    },
    {
        "title": "Yoga by the Pyramids",
        "subtitle": "Sunrise yoga session",
        "description": "<p>Start your day with yoga and meditation at the Pyramids of Giza.</p>",
        "category": "sports_fitness",
        "tags": ["yoga", "wellness", "pyramids", "giza"],
        "venue_name": "Giza Pyramids Complex",
        "city": "Giza",
        "country": "Egypt",
        "organizer_name": "Wellness Egypt"
    },
    {
        "title": "Beach Volleyball Tournament",
        "subtitle": "Sahel's biggest beach sports event",
        "description": "<p>Competitive beach volleyball tournament with prizes and entertainment.</p>",
        "category": "sports_fitness",
        "tags": ["volleyball", "beach", "sports", "sahel"],
        "venue_name": "Marassi Beach",
        "city": "Sahel",
        "country": "Egypt",
        "organizer_name": "Beach Sports Egypt"
    },
    {
        "title": "CrossFit Competition Cairo",
        "subtitle": "Test your fitness limits",
        "description": "<p>Regional CrossFit competition for athletes of all levels.</p>",
        "category": "sports_fitness",
        "tags": ["crossfit", "fitness", "competition", "cairo"],
        "venue_name": "New Cairo Sports Club",
        "city": "New Cairo",
        "country": "Egypt",
        "organizer_name": "CrossFit Egypt"
    },
    
    # Festivals & Fairs
    {
        "title": "Cairo Food Festival",
        "subtitle": "Taste Egypt and the world",
        "description": "<p>Three days of culinary delights featuring local and international cuisines.</p>",
        "category": "festivals_fairs",
        "tags": ["food", "festival", "cuisine", "cairo"],
        "venue_name": "Cairo Festival City",
        "city": "New Cairo",
        "country": "Egypt",
        "organizer_name": "Food Festivals Egypt"
    },
    {
        "title": "Ramadan Night Market",
        "subtitle": "Traditional crafts and street food",
        "description": "<p>Experience Ramadan traditions with crafts, food, and entertainment.</p>",
        "category": "festivals_fairs",
        "tags": ["ramadan", "market", "tradition", "cairo"],
        "venue_name": "Al-Azhar Park",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Cairo Markets"
    },
    {
        "title": "Spring Flower Festival",
        "subtitle": "Celebrate spring in full bloom",
        "description": "<p>Garden festival featuring flowers, plants, and landscaping workshops.</p>",
        "category": "festivals_fairs",
        "tags": ["flowers", "spring", "garden", "cairo"],
        "venue_name": "Orman Garden",
        "city": "Giza",
        "country": "Egypt",
        "organizer_name": "Green Egypt"
    },
    
    # Workshops & Experiences
    {
        "title": "Photography Masterclass",
        "subtitle": "Learn from award-winning photographers",
        "description": "<p>Full-day workshop covering portrait and landscape photography techniques.</p>",
        "category": "workshops_experiences",
        "tags": ["photography", "workshop", "learning", "cairo"],
        "venue_name": "Cairo Creative Hub",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Photo Academy Egypt"
    },
    {
        "title": "Cooking Class: Egyptian Cuisine",
        "subtitle": "Master traditional Egyptian dishes",
        "description": "<p>Hands-on cooking class learning to prepare authentic Egyptian meals.</p>",
        "category": "workshops_experiences",
        "tags": ["cooking", "cuisine", "workshop", "cairo"],
        "venue_name": "Culinary Arts Academy",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Cook Egypt"
    },
    {
        "title": "Pottery Making Workshop",
        "subtitle": "Create your own ceramic art",
        "description": "<p>Learn traditional pottery techniques and create your own pieces.</p>",
        "category": "workshops_experiences",
        "tags": ["pottery", "art", "workshop", "cairo"],
        "venue_name": "Fagnoon Art School",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Fagnoon"
    },
    {
        "title": "Digital Marketing Bootcamp",
        "subtitle": "Master social media and online marketing",
        "description": "<p>Intensive 3-day bootcamp covering all aspects of digital marketing.</p>",
        "category": "workshops_experiences",
        "tags": ["marketing", "digital", "workshop", "cairo"],
        "venue_name": "GrEEK Campus",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Digital Academy"
    },
    
    # Entertainment & Lifestyle
    {
        "title": "Fashion Week Cairo",
        "subtitle": "Egypt's premier fashion event",
        "description": "<p>Runway shows featuring top Egyptian and international designers.</p>",
        "category": "entertainment_lifestyle",
        "tags": ["fashion", "runway", "design", "cairo"],
        "venue_name": "Four Seasons Nile Plaza",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Fashion Egypt"
    },
    {
        "title": "Luxury Car Show",
        "subtitle": "Exotic cars and supercars on display",
        "description": "<p>Exhibition of the world's most luxurious and exotic automobiles.</p>",
        "category": "entertainment_lifestyle",
        "tags": ["cars", "luxury", "exhibition", "cairo"],
        "venue_name": "Cairo International Convention Center",
        "city": "New Cairo",
        "country": "Egypt",
        "organizer_name": "Auto Shows Egypt"
    },
    {
        "title": "Wine Tasting Evening",
        "subtitle": "Discover Egyptian wines",
        "description": "<p>Guided wine tasting featuring Egypt's finest local vineyards.</p>",
        "category": "entertainment_lifestyle",
        "tags": ["wine", "tasting", "lifestyle", "cairo"],
        "venue_name": "Marriott Mena House",
        "city": "Giza",
        "country": "Egypt",
        "organizer_name": "Wine Egypt"
    },
    
    # Family & Kids
    {
        "title": "Kids Science Fair",
        "subtitle": "Fun experiments and learning",
        "description": "<p>Interactive science fair with hands-on experiments for children.</p>",
        "category": "family_kids",
        "tags": ["kids", "science", "education", "cairo"],
        "venue_name": "Children's Civilization and Creativity Center",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Science for Kids"
    },
    {
        "title": "Family Fun Day at the Zoo",
        "subtitle": "Special activities and animal encounters",
        "description": "<p>Family day with special animal shows, face painting, and activities.</p>",
        "category": "family_kids",
        "tags": ["family", "kids", "zoo", "giza"],
        "venue_name": "Giza Zoo",
        "city": "Giza",
        "country": "Egypt",
        "organizer_name": "Giza Zoo"
    },
    {
        "title": "Puppet Show: Arabian Nights",
        "subtitle": "Classic tales brought to life",
        "description": "<p>Magical puppet show retelling classic Arabian Nights stories.</p>",
        "category": "family_kids",
        "tags": ["kids", "puppet", "show", "cairo"],
        "venue_name": "Cairo Puppet Theater",
        "city": "Cairo",
        "country": "Egypt",
        "organizer_name": "Puppet Theater Cairo"
    },
    {
        "title": "Summer Kids Camp",
        "subtitle": "Week-long adventure for children",
        "description": "<p>Summer camp with sports, arts, crafts, and outdoor activities.</p>",
        "category": "family_kids",
        "tags": ["kids", "camp", "summer", "cairo"],
        "venue_name": "Katameya Heights",
        "city": "New Cairo",
        "country": "Egypt",
        "organizer_name": "Kids Camp Egypt"
    }
]

def generate_datetime(days_from_now):
    """Generate datetime string for event"""
    date = datetime.now() + timedelta(days=days_from_now)
    start = date.replace(hour=random.choice([10, 14, 16, 18, 19, 20]), minute=0, second=0)
    end = start + timedelta(hours=random.choice([2, 3, 4, 5, 6]))
    return start.isoformat() + "Z", end.isoformat() + "Z"

def create_event(event_data, index):
    """Create a single event"""
    # Generate dates (spread events over next 90 days)
    days_offset = (index * 3) % 90
    start_dt, end_dt = generate_datetime(days_offset)
    
    # Complete event data
    full_event = {
        **event_data,
        "start_datetime": start_dt,
        "end_datetime": end_dt,
        "status": "draft",
        "seo_slug": event_data["title"].lower().replace(" ", "-").replace("'", "")
    }
    
    # Add optional address
    if event_data.get("venue_name"):
        full_event["address"] = f"{event_data['venue_name']}, {event_data['city']}"
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/events",
            headers=headers,
            json=full_event
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Created: {full_event['title']} (ID: {result['shopify_product_id']})")
            return True
        else:
            print(f"❌ Failed: {full_event['title']}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating {full_event['title']}: {str(e)}")
        return False

def main():
    print("🚀 Creating 30 draft events for testing...\n")
    print("=" * 60)
    
    success_count = 0
    for i, event in enumerate(EVENTS, 1):
        print(f"\n[{i}/30] ", end="")
        if create_event(event, i):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"\n✨ Done! Created {success_count}/30 events")
    print(f"\nView events: GET {API_BASE_URL}/events?status=draft&limit=50")

if __name__ == "__main__":
    main()
