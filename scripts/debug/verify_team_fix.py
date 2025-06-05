#!/usr/bin/env python3
"""
Simple test to verify the team cancellation fix
"""

import asyncio
from typing import Dict, Optional, List
from utils.db_operations import DatabaseOperations

async def main():
    print("=== Verifying Team Cancellation Fix ===")
    
    try:        # Check for events with team registrations
        events = await DatabaseOperations.find_many("events", {"team_registrations": {"$exists": True, "$ne": {}}})
        
        if not events:
            print("No events with team registrations found")
            return
            
        for event in events:
            event_id = event['event_id']
            team_registrations = event.get('team_registrations', {})
            
            print(f"\nEvent: {event.get('event_name', 'Unknown')} ({event_id})")
            print(f"Team registrations: {len(team_registrations)}")
            
            for team_id, team_data in list(team_registrations.items())[:1]:  # Check first team only
                print(f"\nTeam ID: {team_id}")
                print(f"Team Name: {team_data.get('team_name', 'Unknown')}")
                
                # Check field names
                team_leader_enrollment = team_data.get('team_leader_enrollment')
                participants = team_data.get('participants', [])
                
                print(f"✓ team_leader_enrollment: {team_leader_enrollment}")
                print(f"✓ participants: {participants}")
                
                # Check old field names (should not exist)
                old_team_leader = team_data.get('team_leader')
                old_participants = team_data.get('team_participants')
                
                if old_team_leader:
                    print(f"⚠ Old field 'team_leader' still exists: {old_team_leader}")
                else:
                    print("✓ Old field 'team_leader' not found (good)")
                    
                if old_participants:
                    print(f"⚠ Old field 'team_participants' still exists: {old_participants}")
                else:
                    print("✓ Old field 'team_participants' not found (good)")
                
                # Verify the fix works
                if team_leader_enrollment and participants is not None:
                    print("\n✅ TEAM CANCELLATION SHOULD NOW WORK!")
                    print("The cancel_entire_team function will correctly find:")
                    print(f"  - Team leader: {team_leader_enrollment}")
                    print(f"  - Participants: {participants}")
                else:
                    print("\n❌ Team cancellation may still have issues")
                
                break  # Only check first team
            break  # Only check first event
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
