#!/usr/bin/env python3
"""Test script to check team registration datetime from event data"""

import asyncio
import sys
import os
from datetime import datetime

# Add the admin directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db_operations import DatabaseOperations
from config.database import Database

async def test_team_registration_datetime():
    """Test team registration datetime from event data"""
    print("=== Testing Team Registration DateTime from Event Data ===")
    
    try:
        # Connect to database
        await Database.connect_db()
        print("✅ Connected to database")
        
        # Find events with team registrations
        events = await DatabaseOperations.find_many(
            "events", 
            {"team_registrations": {"$exists": True, "$ne": {}}},
            limit=5
        )
        
        print(f"\nFound {len(events)} events with team registrations")
        
        for event in events:
            event_id = event.get('event_id', 'Unknown')
            event_name = event.get('event_name', 'Unknown')
            team_registrations = event.get('team_registrations', {})
            
            print(f"\n📋 Event: {event_id} - {event_name}")
            print(f"   Team Registrations Count: {len(team_registrations)}")
            
            for team_reg_id, team_data in team_registrations.items():
                team_name = team_data.get('team_name', 'Unknown')
                leader_enrollment = team_data.get('team_leader_enrollment', 'Unknown')
                participants = team_data.get('participants', [])
                reg_date = team_data.get('registration_date')
                
                print(f"\n  Team Registration ID: {team_reg_id}")
                print(f"  Team Name: {team_name}")
                print(f"  Leader: {leader_enrollment}")
                print(f"  Participants: {participants}")
                print(f"  Registration Date: {reg_date}")
                print(f"  Date Type: {type(reg_date)}")
                
                if reg_date:
                    if isinstance(reg_date, datetime):
                        formatted = reg_date.strftime('%d %B %Y at %I:%M %p')
                        print(f"  ✅ Formatted: {formatted}")
                    elif isinstance(reg_date, str):
                        try:
                            parsed_dt = datetime.fromisoformat(reg_date.replace('Z', '+00:00'))
                            formatted = parsed_dt.strftime('%d %B %Y at %I:%M %p')
                            print(f"  ✅ Parsed & Formatted: {formatted}")
                        except Exception as e:
                            print(f"  ❌ String parsing failed: {e}")
                    else:
                        print(f"  ⚠️  Unknown datetime type: {type(reg_date)}")
                else:
                    print(f"  ❌ No registration date found")
                
                print("  " + "-" * 50)
        
        # Also check a specific student's team participation
        print("\n=== Checking Student Team Participation ===")
        students = await DatabaseOperations.find_many(
            "students", 
            {"event_participations": {"$exists": True, "$ne": {}}},
            limit=3
        )
        
        for student in students:
            enrollment = student.get('enrollment_no', 'Unknown')
            name = student.get('full_name', 'Unknown')
            participations = student.get('event_participations', {})
            
            print(f"\n👤 Student: {enrollment} - {name}")
            
            for event_id, participation in participations.items():
                reg_type = participation.get('registration_type', 'unknown')
                team_reg_id = participation.get('team_registration_id')
                reg_datetime = participation.get('registration_datetime')
                
                if reg_type in ['team_leader', 'team_participant'] and team_reg_id:
                    print(f"  📅 Event: {event_id}")
                    print(f"     Type: {reg_type}")
                    print(f"     Team Registration ID: {team_reg_id}")
                    print(f"     Student Registration DateTime: {reg_datetime}")
                    
                    # Now find the actual team registration date from event data
                    event_data = await DatabaseOperations.find_one("events", {"event_id": event_id})
                    if event_data:
                        team_regs = event_data.get('team_registrations', {})
                        team_reg_data = team_regs.get(team_reg_id, {})
                        actual_reg_date = team_reg_data.get('registration_date')
                        
                        print(f"     🎯 Actual Team Registration Date: {actual_reg_date}")
                        print(f"     🎯 Date Type: {type(actual_reg_date)}")
                        
                        if actual_reg_date:
                            if isinstance(actual_reg_date, datetime):
                                formatted = actual_reg_date.strftime('%d %B %Y at %I:%M %p')
                                print(f"     ✅ Formatted: {formatted}")
                            elif isinstance(actual_reg_date, str):
                                try:
                                    parsed_dt = datetime.fromisoformat(actual_reg_date.replace('Z', '+00:00'))
                                    formatted = parsed_dt.strftime('%d %B %Y at %I:%M %p')
                                    print(f"     ✅ Parsed & Formatted: {formatted}")
                                except Exception as e:
                                    print(f"     ❌ String parsing failed: {e}")
                    
                    print("     " + "-" * 40)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await Database.close_db()

if __name__ == "__main__":
    asyncio.run(test_team_registration_datetime())
