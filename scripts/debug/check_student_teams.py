#!/usr/bin/env python3
"""
Check student records for team participation data
"""

import asyncio
from typing import Dict, Optional, List
from utils.db_operations import DatabaseOperations

async def main():
    print("=== Checking Student Team Participation Records ===")
    
    try:
        # Get all students
        students = await DatabaseOperations.find_many("students", {})
        
        print(f"Total students found: {len(students)}")
        
        team_participants = []
        
        for student in students:
            enrollment_no = student.get('enrollment_no', 'Unknown')
            participations = student.get('event_participations', {})
            
            for event_id, participation in participations.items():
                team_registration_id = participation.get('team_registration_id')
                registration_type = participation.get('registration_type')
                
                if team_registration_id or registration_type in ['team_leader', 'team_participant']:
                    team_participants.append({
                        'enrollment': enrollment_no,
                        'event_id': event_id,
                        'team_registration_id': team_registration_id,
                        'registration_type': registration_type
                    })
        
        print(f"\nStudents with team participation: {len(team_participants)}")
        
        for participant in team_participants:
            print(f"  {participant['enrollment']} - {participant['event_id']} - {participant['registration_type']} - Team: {participant['team_registration_id']}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
