#!/usr/bin/env python3
"""
Test script to verify that both individual and team registration dates 
are properly retrieved from the correct sources.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils.db_operations import DatabaseOperations
from config.database import Database
from routes.client.event_registration import get_registration_datetime_from_team_data, get_team_info_for_registration

async def test_both_registration_types():
    """Test both individual and team registration datetime retrieval"""
    print("=== Testing Individual vs Team Registration DateTime Fix ===")
    
    try:
        # Connect to database
        await Database.connect_db()
        print("✅ Connected to database")
        
        # Test with multiple students to find both individual and team registrations
        test_enrollments = ["22BEIT30043", "22BEIT30044", "22BEIT30045", "22BEIT30046"]
        
        for student_enrollment in test_enrollments:
            student_data = await DatabaseOperations.find_one("students", {"enrollment_no": student_enrollment})
            
            if not student_data:
                print(f"❌ Student {student_enrollment} not found")
                continue
                
            print(f"\n👤 Testing with student: {student_data.get('full_name')} ({student_enrollment})")
            
            # Get their event participations
            event_participations = student_data.get('event_participations', {})
            
            if not event_participations:
                print("   📝 No event participations found")
                continue
            
            for event_id, participation in event_participations.items():
                print(f"\n📅 Event: {event_id}")
                reg_type = participation.get('registration_type', 'individual')
                print(f"   Registration Type: {reg_type}")
                
                # Show what's in the participation data
                print(f"   📊 Raw participation data:")
                print(f"      registration_datetime: {participation.get('registration_datetime')}")
                print(f"      registration_date: {participation.get('registration_date')}")
                print(f"      team_registration_id: {participation.get('team_registration_id')}")
                
                # Get the event data
                event = await DatabaseOperations.find_one("events", {"event_id": event_id})
                if not event:
                    print(f"   ❌ Event not found")
                    continue
                
                # If it's a team registration, show team data from event
                if reg_type in ['team_leader', 'team_participant']:
                    team_reg_id = participation.get('team_registration_id')
                    if team_reg_id:
                        team_registrations = event.get('team_registrations', {})
                        team_data = team_registrations.get(team_reg_id, {})
                        print(f"      Team registration_date (from event): {team_data.get('registration_date')}")
                    
                # Test our helper function
                actual_datetime = await get_registration_datetime_from_team_data(event, participation)
                print(f"   🎯 Retrieved Registration DateTime: {actual_datetime}")
                
                if actual_datetime:
                    if isinstance(actual_datetime, datetime):
                        formatted_date = actual_datetime.strftime('%d %B %Y at %H:%M')
                        print(f"   ✅ Formatted: {formatted_date}")
                    else:
                        print(f"   ⚠️  Not a datetime object: {type(actual_datetime)} - {actual_datetime}")
                else:
                    print(f"   ❌ No registration datetime found")
                
                print("   " + "-" * 50)
            
            # Stop after finding some registrations to avoid too much output
            if event_participations:
                break
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Database.close_db()
        print("🔌 Closed database connection")

if __name__ == "__main__":
    asyncio.run(test_both_registration_types())
