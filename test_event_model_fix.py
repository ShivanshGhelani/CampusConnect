#!/usr/bin/env python3
"""
Test script for event model with attendances
"""

import asyncio
from utils.db_operations import DatabaseOperations

async def test_event_model():
    """Test the Event model with the updated attendances field"""
    
    print("🎯 EVENT MODEL TEST")
    print("=" * 50)
    
    # Get test event
    event_id = "GREEN_INNOVATION_HACKATHON_2025"
    try:
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        
        if not event:
            print(f"❌ Event not found: {event_id}")
            return
            
        print(f"✅ Event found: {event.get('event_name')}")
        
        # Check attendances
        attendances = event.get('attendances', {})
        print(f"📊 Number of attendances: {len(attendances)}")
        
        # Check one attendance entry
        if attendances:
            attendance_id = list(attendances.keys())[0]
            attendance_data = attendances[attendance_id]
            print(f"\nSample attendance entry ({attendance_id}):")
            for key, value in attendance_data.items():
                print(f"   {key}: {value}")
        else:
            print("No attendance entries found")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print("\nTest completed")

if __name__ == "__main__":
    asyncio.run(test_event_model())
