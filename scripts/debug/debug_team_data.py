import asyncio
from utils.db_operations import DatabaseOperations

async def check_data():    # Check for team registrations
    students = await DatabaseOperations.find_many('students', {'event_participations': {'$exists': True}}, limit=5)
    print('=== STUDENT DATA ===')
    for student in students:
        participations = student.get('event_participations', {})
        if participations:
            print(f'Student: {student.get("enrollment_no")} - {student.get("full_name")}')
            for event_id, participation in participations.items():
                reg_type = participation.get('registration_type')
                team_reg_id = participation.get('team_registration_id')
                print(f'  Event: {event_id} | Type: {reg_type} | Team ID: {team_reg_id}')
            print()
      # Check events data
    events = await DatabaseOperations.find_many('events', {'team_registrations': {'$exists': True}}, limit=3)
    print('=== EVENT DATA ===')
    for event in events:
        event_id = event.get('event_id')
        team_regs = event.get('team_registrations', {})
        print(f'Event: {event_id}')
        for team_id, team_data in team_regs.items():
            leader = team_data.get('team_leader_enrollment', 'unknown')
            participants = team_data.get('participants', [])
            print(f'  Team ID: {team_id} | Leader: {leader} | Participants: {participants}')
        print()

asyncio.run(check_data())
