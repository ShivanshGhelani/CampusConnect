#!/usr/bin/env python3
"""
Script to add sample events to the database for testing the pie chart
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import MONGODB_URL

async def add_sample_events():
    """Add sample events to the database for chart testing"""
    
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client.ucg_v2
    events_collection = db.events
    
    # Sample events with different statuses for testing
    sample_events = [
        {
            "id": "chart_test_001",
            "title": "Tech Innovation Summit 2025",
            "description": "Annual technology summit featuring latest innovations",
            "status": "active",
            "sub_status": "registration_open",
            "type": "hackathon",
            "venue": "Main Auditorium",
            "max_participants": 200,
            "registration_start": datetime.now(timezone.utc) - timedelta(days=5),
            "registration_end": datetime.now(timezone.utc) + timedelta(days=10),
            "event_start": datetime.now(timezone.utc) + timedelta(days=15),
            "event_end": datetime.now(timezone.utc) + timedelta(days=17),
            "created_at": datetime.now(timezone.utc),
            "created_by": "admin"
        },
        {
            "id": "chart_test_002",
            "title": "AI Workshop Series",
            "description": "Hands-on AI workshops for students",
            "status": "active",
            "sub_status": "live",
            "type": "workshop",
            "venue": "Computer Lab A",
            "max_participants": 50,
            "registration_start": datetime.now(timezone.utc) - timedelta(days=20),
            "registration_end": datetime.now(timezone.utc) - timedelta(days=2),
            "event_start": datetime.now(timezone.utc) - timedelta(hours=2),
            "event_end": datetime.now(timezone.utc) + timedelta(hours=4),
            "created_at": datetime.now(timezone.utc),
            "created_by": "admin"
        },
        {
            "id": "chart_test_003",
            "title": "Campus Career Fair",
            "description": "Connect with top employers and explore career opportunities",
            "status": "active",
            "sub_status": "registration_not_started",
            "type": "career_fair",
            "venue": "Sports Complex",
            "max_participants": 500,
            "registration_start": datetime.now(timezone.utc) + timedelta(days=5),
            "registration_end": datetime.now(timezone.utc) + timedelta(days=25),
            "event_start": datetime.now(timezone.utc) + timedelta(days=30),
            "event_end": datetime.now(timezone.utc) + timedelta(days=30, hours=8),
            "created_at": datetime.now(timezone.utc),
            "created_by": "admin"
        },
        {
            "id": "chart_test_004",
            "title": "Spring Coding Contest",
            "description": "Competitive programming challenge for all skill levels",
            "status": "completed",
            "sub_status": "completed",
            "type": "competition",
            "venue": "Online Platform",
            "max_participants": 100,
            "registration_start": datetime.now(timezone.utc) - timedelta(days=30),
            "registration_end": datetime.now(timezone.utc) - timedelta(days=15),
            "event_start": datetime.now(timezone.utc) - timedelta(days=10),
            "event_end": datetime.now(timezone.utc) - timedelta(days=10, hours=-4),
            "created_at": datetime.now(timezone.utc),
            "created_by": "admin"
        },
        {
            "id": "chart_test_005",
            "title": "Data Science Bootcamp",
            "description": "Intensive bootcamp covering data science fundamentals",
            "status": "active",
            "sub_status": "registration_open",
            "type": "workshop",
            "venue": "Library Conference Room",
            "max_participants": 30,
            "registration_start": datetime.now(timezone.utc) - timedelta(days=3),
            "registration_end": datetime.now(timezone.utc) + timedelta(days=7),
            "event_start": datetime.now(timezone.utc) + timedelta(days=12),
            "event_end": datetime.now(timezone.utc) + timedelta(days=14),
            "created_at": datetime.now(timezone.utc),
            "created_by": "admin"
        },
        {
            "id": "chart_test_006",
            "title": "Cybersecurity Seminar",
            "description": "Learn about latest cybersecurity threats and defenses",
            "status": "completed",
            "sub_status": "completed",
            "type": "seminar",
            "venue": "Lecture Hall B",
            "max_participants": 75,
            "registration_start": datetime.now(timezone.utc) - timedelta(days=25),
            "registration_end": datetime.now(timezone.utc) - timedelta(days=12),
            "event_start": datetime.now(timezone.utc) - timedelta(days=8),
            "event_end": datetime.now(timezone.utc) - timedelta(days=8, hours=-3),
            "created_at": datetime.now(timezone.utc),
            "created_by": "admin"
        }
    ]
    
    try:
        # Check if sample events already exist
        existing_count = await events_collection.count_documents({"id": {"$regex": "^chart_test_"}})
        
        if existing_count > 0:
            print(f"Found {existing_count} existing test events. Removing them first...")
            await events_collection.delete_many({"id": {"$regex": "^chart_test_"}})
            print("Existing test events removed.")
        
        # Insert new sample events
        result = await events_collection.insert_many(sample_events)
        
        print(f"✅ Successfully added {len(result.inserted_ids)} sample events!")
        print("\nSample Events Added:")
        print("-" * 50)
        
        for event in sample_events:
            print(f"• {event['title']} ({event['id']})")
            print(f"  Status: {event['status']} - {event['sub_status']}")
            print()
        
        # Verify the data
        total_events = await events_collection.count_documents({})
        print(f"Total events in database: {total_events}")
        
        # Count by status for chart verification
        status_counts = {
            "registration_open": await events_collection.count_documents({
                "status": "active", "sub_status": "registration_open"
            }),
            "live": await events_collection.count_documents({
                "status": "active", "sub_status": "live"
            }),
            "registration_not_started": await events_collection.count_documents({
                "status": "active", "sub_status": "registration_not_started"
            }),
            "completed": await events_collection.count_documents({
                "status": "completed"
            })
        }
        
        print("\nChart Data Verification:")
        print("-" * 30)
        for key, value in status_counts.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        
        chart_total = sum(status_counts.values())
        print(f"\nTotal for chart: {chart_total}")
        
        print("\n✅ The dashboard pie chart should now display with actual data!")
        print("📊 Navigate to http://localhost:8000/admin/dashboard to see the chart.")
        
    except Exception as e:
        print(f"❌ Error adding sample events: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    print("Adding Sample Events for Chart Testing")
    print("=" * 50)
    asyncio.run(add_sample_events())
