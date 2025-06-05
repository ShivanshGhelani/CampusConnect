#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db_operations import DatabaseOperations

async def check_current_data():
    """Check current team data state"""
    
    print("=== Current Team Data State ===\n")
    
    event_id = "AI_ML_BO_30043"
    team_registration_id = "TEAM_AI_ML_BO_30043_B953"
    
    try:
        # Check event data
        event_data = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if event_data:
            team_registrations = event_data.get('team_registrations', {})
            registrations = event_data.get('registrations', {})
            
            print(f"Event found: {event_data.get('title', 'Unknown')}")
            print(f"Team registrations: {list(team_registrations.keys())}")
            print(f"Total individual registrations: {len(registrations)}")
            
            if team_registration_id in team_registrations:
                team_reg = team_registrations[team_registration_id]
                print(f"\nTeam Details:")
                print(f"  Leader: {team_reg.get('team_leader')}")
                print(f"  Participants: {team_reg.get('team_participants', [])}")
                print(f"  Team Name: {team_reg.get('team_name')}")
                
                # Check individual registrations for team members
                team_leader = team_reg.get('team_leader')
                team_participants = team_reg.get('team_participants', [])
                all_members = [team_leader] + team_participants
                
                team_member_regs = {}
                for reg_id, enrollment in registrations.items():
                    if enrollment in all_members:
                        team_member_regs[reg_id] = enrollment
                
                print(f"\nTeam member individual registrations: {len(team_member_regs)}")
                for reg_id, enrollment in team_member_regs.items():
                    print(f"  {reg_id}: {enrollment}")
            else:
                print(f"\nTeam registration {team_registration_id} NOT FOUND")
        else:
            print("Event not found!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_current_data())
