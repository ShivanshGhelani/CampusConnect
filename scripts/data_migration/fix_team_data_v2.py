#!/usr/bin/env python3
"""
Fix existing team registration data by updating team_registration_id
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db_operations import DatabaseOperations

async def fix_team_registration_data():
    """Fix existing team registration data by updating team_registration_id"""
    
    print("Starting team registration data fix...")
    
    # Get all events with team registrations
    events = await DatabaseOperations.find_many('events', {"team_registrations": {"$exists": True, "$ne": {}}})
    
    for event in events:
        event_id = event["event_id"]
        team_registrations = event.get("team_registrations", {})
        
        print(f"\nProcessing event: {event_id}")
        print(f"Found {len(team_registrations)} team registrations")
        
        for team_id, team_data in team_registrations.items():
            leader_enrollment = team_data.get("team_leader_enrollment")  # Fixed field name
            participants = team_data.get("participants", [])
            
            print(f"  Team ID: {team_id}")
            print(f"  Leader: {leader_enrollment}")
            print(f"  Participants: {participants}")
            
            # Update leader's team_registration_id
            if leader_enrollment:
                result = await DatabaseOperations.update_one(
                    'students',
                    {
                        "enrollment_no": leader_enrollment,
                        f"event_participations.{event_id}": {"$exists": True}
                    },
                    {
                        "$set": {
                            f"event_participations.{event_id}.team_registration_id": team_id
                        }
                    }
                )
                print(f"    Updated leader {leader_enrollment}: {'Success' if result else 'Failed'}")
            
            # Update participants' team_registration_id
            for participant_enrollment in participants:
                result = await DatabaseOperations.update_one(
                    'students',
                    {
                        "enrollment_no": participant_enrollment,
                        f"event_participations.{event_id}": {"$exists": True}
                    },
                    {
                        "$set": {
                            f"event_participations.{event_id}.team_registration_id": team_id
                        }
                    }
                )
                print(f"    Updated participant {participant_enrollment}: {'Success' if result else 'Failed'}")
    
    print("\n=== VERIFICATION ===")
    # Verify the fix
    students = await DatabaseOperations.find_many('students', {"event_participations": {"$exists": True, "$ne": {}}})
    
    for student in students:
        enrollments = student.get("enrollment_no", "Unknown")
        name = student.get("full_name", "Unknown")
        event_participations = student.get("event_participations", {})
        
        print(f"Student: {enrollments} - {name}")
        for event_id, participation in event_participations.items():
            reg_type = participation.get("registration_type", "unknown")
            team_id = participation.get("team_registration_id", "None")
            team_name = participation.get("team_name", "None")
            print(f"  Event: {event_id} | Type: {reg_type} | Team ID: {team_id} | Team Name: {team_name}")
    
    print("\nTeam registration data fix completed!")

if __name__ == "__main__":
    asyncio.run(fix_team_registration_data())
