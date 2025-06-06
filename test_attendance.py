#!/usr/bin/env python3
"""
Test script to debug attendance marking functionality
"""

import asyncio
from utils.db_operations import DatabaseOperations
from utils.event_lifecycle_helpers import mark_attendance

async def test_attendance_marking():
    """Test the attendance marking functionality"""
    
    # Test data
    enrollment_no = "22BEIT30043"
    event_id = "GREEN_INNOVATION_HACKATHON_2025"
    
    print(f"Testing attendance marking for student {enrollment_no} in event {event_id}")
    print("=" * 60)
    
    # 1. Check student data
    print("1. Checking student data...")
    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
    if not student_data:
        print("ERROR: Student not found!")
        return
    
    print(f"   Student found: {student_data.get('full_name')}")
    
    # 2. Check event participations
    print("2. Checking event participations...")
    event_participations = student_data.get('event_participations', {})
    
    if event_id not in event_participations:
        print(f"   ERROR: Student not registered for event {event_id}")
        print(f"   Available events: {list(event_participations.keys())}")
        return
    
    participation = event_participations[event_id]
    registration_id = participation.get('registration_id')
    attendance_id = participation.get('attendance_id')
    
    print(f"   Registration ID: {registration_id}")
    print(f"   Current Attendance ID: {attendance_id}")
    print(f"   Registration Type: {participation.get('registration_type')}")
    
    if not registration_id:
        print("   ERROR: No registration ID found!")
        return
    
    # 3. Check event data
    print("3. Checking event data...")
    event_data = await DatabaseOperations.find_one("events", {"event_id": event_id})
    if not event_data:
        print("   ERROR: Event not found!")
        return
    
    print(f"   Event name: {event_data.get('event_name')}")
    print(f"   Event status: {event_data.get('status')}")
    print(f"   Event sub_status: {event_data.get('sub_status')}")
    
    # Check registrations
    registrations = event_data.get('registrations', {})
    if registration_id in registrations:
        print(f"   ✓ Student found in event registrations")
    else:
        print(f"   ⚠ Student NOT found in event registrations")
        print(f"   Available registrations: {list(registrations.keys())[:5]}...")
    
    # 4. Test attendance marking if not already marked
    if attendance_id:
        print(f"4. Attendance already marked with ID: {attendance_id}")
    else:
        print("4. Testing attendance marking...")
        success, new_attendance_id, message = await mark_attendance(
            enrollment_no=enrollment_no,
            event_id=event_id,
            present=True
        )
        
        print(f"   Success: {success}")
        print(f"   Attendance ID: {new_attendance_id}")
        print(f"   Message: {message}")
        
        if success:
            # Verify the attendance was stored
            updated_student = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
            new_participation = updated_student.get('event_participations', {}).get(event_id, {})
            print(f"   ✓ Stored attendance ID: {new_participation.get('attendance_id')}")
            
            # Check event data
            updated_event = await DatabaseOperations.find_one("events", {"event_id": event_id})
            attendances = updated_event.get('attendances', {})
            print(f"   ✓ Event attendances count: {len(attendances)}")
    
    print("=" * 60)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_attendance_marking())
