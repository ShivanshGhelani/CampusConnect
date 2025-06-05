import asyncio
from utils.db_operations import DatabaseOperations

async def check_student_data():
    # Check upcoming events with registration_open sub_status
    upcoming_events = await DatabaseOperations.find_many('events', {'status': 'upcoming'})
    print(f'Found {len(upcoming_events)} upcoming events:')
    for event in upcoming_events:
        sub_status = event.get('sub_status')
        print(f'- {event.get("event_id")}: {event.get("event_name")} (status: {event.get("status")}, sub_status: {sub_status})')
    
    # Check if any student is registered for upcoming events
    students = await DatabaseOperations.find_many('students', {}, limit=5)
    for student in students:
        event_participations = student.get('event_participations', {})
        if event_participations:
            print(f'\nStudent: {student.get("enrollment_no")} - {student.get("full_name")}')
            for event_id, participation in event_participations.items():
                reg_type = participation.get('registration_type')
                # Check event details
                event = await DatabaseOperations.find_one('events', {'event_id': event_id})
                if event:
                    status = event.get('status')
                    sub_status = event.get('sub_status')
                    print(f'  Registered for: {event_id} (status: {status}, sub_status: {sub_status}, reg_type: {reg_type})')
                    
                    # Check if cancel button should appear
                    can_cancel = status == 'upcoming' and sub_status == 'registration_open'
                    can_manage_team = reg_type == 'team_leader' and status == 'upcoming' and sub_status == 'registration_open'
                    print(f'    Can cancel: {can_cancel}, Can manage team: {can_manage_team}')

if __name__ == "__main__":
    asyncio.run(check_student_data())
