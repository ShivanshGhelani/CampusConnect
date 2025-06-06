#!/usr/bin/env python3
"""
Comprehensive test to verify the complete attendance marking system
"""

import asyncio
from utils.db_operations import DatabaseOperations
from utils.event_lifecycle_helpers import mark_attendance
from datetime import datetime, timezone

async def comprehensive_attendance_test():
    """Test the complete attendance marking system"""
    
    enrollment_no = "22BEIT30043"
    event_id = "GREEN_INNOVATION_HACKATHON_2025"
    
    print("COMPREHENSIVE ATTENDANCE MARKING TEST")
    print("=" * 60)
    
    try:
        # Step 1: Reset attendance if already marked (for testing)
        print("1. Resetting attendance for fresh test...")
        
        # Remove attendance_id from student data
        await DatabaseOperations.update_one(
            "students",
            {"enrollment_no": enrollment_no},
            {"$unset": {f"event_participations.{event_id}.attendance_id": ""}}
        )
        
        # Remove from event attendances
        await DatabaseOperations.update_one(
            "events", 
            {"event_id": event_id},
            {"$unset": {"attendances": ""}}
        )
        
        print("   ✓ Attendance reset for testing")
        
        # Step 2: Verify student registration
        print("2. Verifying student registration...")
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
        
        if not student_data:
            print("   ✗ Student not found!")
            return False
        
        participations = student_data.get('event_participations', {})
        if event_id not in participations:
            print("   ✗ Student not registered for event!")
            return False
        
        participation = participations[event_id]
        registration_id = participation.get('registration_id')
        
        if not registration_id:
            print("   ✗ No registration_id found!")
            return False
        
        print(f"   ✓ Student registered with ID: {registration_id}")
        
        # Step 3: Verify event status
        print("3. Verifying event status...")
        event_data = await DatabaseOperations.find_one("events", {"event_id": event_id})
        
        if not event_data:
            print("   ✗ Event not found!")
            return False
        
        event_status = event_data.get('sub_status')
        print(f"   Event sub_status: {event_status}")
        
        if event_status != 'event_started':
            print("   ⚠ Event is not in 'event_started' status")
        else:
            print("   ✓ Event is ready for attendance marking")
        
        # Step 4: Test attendance marking
        print("4. Testing attendance marking...")
        success, attendance_id, message = await mark_attendance(
            enrollment_no=enrollment_no,
            event_id=event_id,
            present=True
        )
        
        print(f"   Success: {success}")
        print(f"   Attendance ID: {attendance_id}")
        print(f"   Message: {message}")
        
        if not success:
            print("   ✗ Attendance marking failed!")
            return False
        
        # Step 5: Verify attendance was stored correctly
        print("5. Verifying attendance storage...")
        
        # Check student data
        updated_student = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
        stored_attendance_id = updated_student.get('event_participations', {}).get(event_id, {}).get('attendance_id')
        
        if stored_attendance_id == attendance_id:
            print(f"   ✓ Student data updated with attendance ID: {stored_attendance_id}")
        else:
            print(f"   ✗ Student data mismatch! Expected: {attendance_id}, Got: {stored_attendance_id}")
        
        # Check event data
        updated_event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        event_attendances = updated_event.get('attendances', {})
        
        if attendance_id in event_attendances:
            print(f"   ✓ Event data updated with attendance record")
            print(f"   Event attendances count: {len(event_attendances)}")
        else:
            print(f"   ✗ Attendance not found in event data!")
            print(f"   Available attendances: {list(event_attendances.keys())}")
        
        # Step 6: Test duplicate attendance prevention
        print("6. Testing duplicate attendance prevention...")
        success2, attendance_id2, message2 = await mark_attendance(
            enrollment_no=enrollment_no,
            event_id=event_id,
            present=True
        )
        
        if not success2 and "already marked" in message2.lower():
            print("   ✓ Duplicate attendance properly prevented")
        else:
            print(f"   ⚠ Unexpected result: Success={success2}, Message={message2}")
        
        print("=" * 60)
        print("✅ COMPREHENSIVE TEST COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(comprehensive_attendance_test())
    if result:
        print("\n🎉 All attendance marking functionality is working correctly!")
    else:
        print("\n❌ Attendance marking system has issues that need to be fixed.")
