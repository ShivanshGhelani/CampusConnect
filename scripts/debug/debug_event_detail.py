#!/usr/bin/env python3
"""
Debug event data structure in detail
"""

import asyncio
from utils.db_operations import DatabaseOperations

async def debug_event_data():
    """Debug the event data structure in detail"""
    
    print("=== DETAILED EVENT DATA DEBUG ===")
    
    # Get the specific event
    event = await DatabaseOperations.find_one('events', {"event_id": "AI_ML_BOOTCAMP_2025"})
    
    if event:
        print(f"Event ID: {event['event_id']}")
        print(f"Event Name: {event.get('event_name', 'Unknown')}")
        
        # Check team registrations structure
        team_registrations = event.get("team_registrations", {})
        print(f"\nTeam Registrations Keys: {list(team_registrations.keys())}")
        
        for team_id, team_data in team_registrations.items():
            print(f"\n--- Team ID: {team_id} ---")
            print(f"Full Team Data: {team_data}")
            print(f"Team Data Type: {type(team_data)}")
            print(f"Team Data Keys: {list(team_data.keys()) if isinstance(team_data, dict) else 'Not a dict'}")
            
            if isinstance(team_data, dict):
                leader = team_data.get("leader")  
                participants = team_data.get("participants", [])
                leader_registration_id = team_data.get("leader_registration_id")
                
                print(f"Leader: {leader} (type: {type(leader)})")
                print(f"Leader Registration ID: {leader_registration_id}")
                print(f"Participants: {participants} (type: {type(participants)})")
    else:
        print("Event not found!")

if __name__ == "__main__":
    asyncio.run(debug_event_data())
