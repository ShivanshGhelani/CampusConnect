#!/usr/bin/env python3
"""
Recreate team registration data in event based on student records
"""

import asyncio
from typing import Dict, Optional, List
from utils.db_operations import DatabaseOperations
from datetime import datetime

async def main():
    print("=== Recreating Team Registration Data ===")
    
    try:
        # Get students with team participation
        students = await DatabaseOperations.find_many("students", {})
        
        team_data = {}
        
        for student in students:
            enrollment_no = student.get('enrollment_no', 'Unknown')
            participations = student.get('event_participations', {})
            
            for event_id, participation in participations.items():
                team_registration_id = participation.get('team_registration_id')
                registration_type = participation.get('registration_type')
                
                if team_registration_id:
                    if team_registration_id not in team_data:
                        team_data[team_registration_id] = {
                            'event_id': event_id,
                            'team_name': f"Team {team_registration_id[-4:]}",  # Use last 4 chars as name
                            'team_leader_enrollment': None,
                            'participants': [],
                            'registration_date': datetime.utcnow()
                        }
                    
                    if registration_type == 'team_leader':
                        team_data[team_registration_id]['team_leader_enrollment'] = enrollment_no
                    elif registration_type == 'team_participant':
                        team_data[team_registration_id]['participants'].append(enrollment_no)
        
        print(f"Found team data: {len(team_data)} teams")
        
        for team_id, data in team_data.items():
            print(f"\nTeam: {team_id}")
            print(f"  Event: {data['event_id']}")
            print(f"  Leader: {data['team_leader_enrollment']}")
            print(f"  Participants: {data['participants']}")
            
            # Add team registration back to event
            event_id = data['event_id']
            team_registration = {
                'team_registration_id': team_id,
                'team_name': data['team_name'],
                'team_leader_enrollment': data['team_leader_enrollment'],
                'participants': data['participants'],
                'registration_date': data['registration_date']
            }
            
            result = await DatabaseOperations.update_one(
                "events",
                {"event_id": event_id},
                {"$set": {f"team_registrations.{team_id}": team_registration}}
            )
            
            print(f"  Added to event: {result}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
