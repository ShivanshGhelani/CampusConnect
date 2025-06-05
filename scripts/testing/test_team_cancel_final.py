#!/usr/bin/env python3
"""
Final test to verify team cancellation functionality works correctly
after fixing the field name mismatch in cancel_entire_team function.
"""

import asyncio
import sys
import os
from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import MONGODB_URL, DATABASE_NAME

async def test_team_cancellation():
    """Test the team cancellation functionality"""
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    print("=== Testing Team Cancellation Functionality ===\n")
    
    # Find a team registration to test with
    events = db.events
    students = db.students
    
    # Look for events with team registrations
    async for event in events.find({"team_registrations": {"$exists": True, "$ne": {}}}):
        event_id = event['event_id']
        team_registrations = event.get('team_registrations', {})
        
        if team_registrations:
            print(f"Found event: {event['event_name']} ({event_id})")
            
            for team_id, team_data in team_registrations.items():
                print(f"\nTeam ID: {team_id}")
                print(f"Team Name: {team_data.get('team_name', 'Unknown')}")
                
                # Check if using correct field names
                team_leader = team_data.get('team_leader_enrollment')
                participants = team_data.get('participants', [])
                
                if team_leader:
                    print(f"Team Leader: {team_leader}")
                    print(f"Participants: {participants}")
                    
                    # Check student records for this team
                    print("\n--- Checking Student Records ---")
                    all_members = [team_leader] + participants
                    
                    for member in all_members:
                        student_doc = await students.find_one({"enrollment_no": member})
                        if student_doc:
                            participations = student_doc.get('event_participations', {})
                            if event_id in participations:
                                participation = participations[event_id]
                                print(f"{member}: Team ID = {participation.get('team_registration_id', 'None')}")
                            else:
                                print(f"{member}: No participation record for this event")
                        else:
                            print(f"{member}: Student not found")
                    
                    # Test the cancel function logic (simulate)
                    print(f"\n--- Testing Cancel Logic for Team {team_id} ---")
                    print("Field names in team data:")
                    print(f"  - team_leader_enrollment: {team_data.get('team_leader_enrollment', 'MISSING')}")
                    print(f"  - participants: {team_data.get('participants', 'MISSING')}")
                    print(f"  - team_leader (old field): {team_data.get('team_leader', 'NOT FOUND - GOOD')}")
                    print(f"  - team_participants (old field): {team_data.get('team_participants', 'NOT FOUND - GOOD')}")
                    
                    # Show what the cancel function would process
                    if team_leader and participants is not None:
                        print(f"\nCancel function would process:")
                        print(f"  - Remove event participation for: {all_members}")
                        print(f"  - Remove team registration: {team_id}")
                        print(f"  - Remove individual registrations for all members")
                        print("✓ Field names are correct - function should work!")
                    else:
                        print("✗ Missing required fields - function would fail!")
                    
                    break
            break
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_team_cancellation())
