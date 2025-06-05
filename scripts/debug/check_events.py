#!/usr/bin/env python3
"""
Check what events exist in the database
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.db_operations import DatabaseOperations

async def main():
    print("=== Checking Events in Database ===")
    
    try:
        # Get all events
        events = await DatabaseOperations.find_many("events", {})
        
        print(f"Total events found: {len(events)}")
        
        for event in events:
            event_id = event.get('event_id', 'Unknown')
            event_name = event.get('event_name', 'Unknown')
            
            print(f"\nEvent: {event_name} ({event_id})")
            
            # Check for team registrations
            team_registrations = event.get('team_registrations', {})
            if team_registrations:
                print(f"  Team registrations: {len(team_registrations)}")
                for team_id, team_data in team_registrations.items():
                    print(f"    Team: {team_data.get('team_name', 'Unknown')} ({team_id})")
            else:
                print("  No team registrations")
            
            # Check for individual registrations
            registrations = event.get('registrations', {})
            if registrations:
                print(f"  Individual registrations: {len(registrations)}")
            else:
                print("  No individual registrations")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
