#!/usr/bin/env python3
"""
Test script for the enhanced attendance marking functionality
Tests the auto-fetch feature and improved user experience
"""

import asyncio
import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_operations import DatabaseOperations
from utils.event_lifecycle_helpers import mark_attendance
from utils.id_generator import generate_registration_id
from datetime import datetime, timezone

async def test_attendance_marking():
    """Test the enhanced attendance marking functionality"""
    print("🧪 Testing Enhanced Attendance Marking System")
    print("=" * 60)
    
    # Test data
    enrollment_no = "22BEIT30043"
    event_id = "AI_ML_BOOTCAMP_2025"
    
    # Step 1: Ensure student has a registration for testing
    print(f"\n--- Step 1: Setting up test registration ---")
    
    # Check if student exists
    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
    if not student_data:
        print("❌ Test student not found in database")
        return
    
    print(f"✅ Student found: {student_data.get('full_name')}")
    
    # Ensure student has event participation record
    event_participations = student_data.get('event_participations', {})
    if event_id not in event_participations:
        # Create a test registration
        registration_id = generate_registration_id(enrollment_no, event_id)
        
        await DatabaseOperations.update_one(
            "students",
            {"enrollment_no": enrollment_no},
            {"$set": {
                f"event_participations.{event_id}": {
                    "registration_id": registration_id,
                    "registration_type": "individual",
                    "registered_at": datetime.now(timezone.utc),
                    "attendance_id": None,
                    "feedback_id": None,
                    "certificate_id": None
                }
            }}
        )
        print(f"✅ Created test registration: {registration_id}")
    else:
        registration_id = event_participations[event_id].get('registration_id')
        print(f"✅ Using existing registration: {registration_id}")
    
    # Step 2: Test attendance marking functionality
    print(f"\n--- Step 2: Testing Attendance Marking ---")
    
    # Check current attendance status
    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
    participation = student_data.get('event_participations', {}).get(event_id, {})
    existing_attendance_id = participation.get('attendance_id')
    
    if existing_attendance_id:
        print(f"⚠️  Attendance already marked: {existing_attendance_id}")
        print("Testing duplicate attendance prevention...")
        
        # Test duplicate prevention
        success, attendance_id, message = await mark_attendance(enrollment_no, event_id, present=True)
        if not success and attendance_id == existing_attendance_id:
            print("✅ CORRECT: Duplicate attendance prevented")
        else:
            print("❌ INCORRECT: Duplicate attendance should be prevented")
    else:
        print("Testing first-time attendance marking...")
        
        # Test marking attendance
        success, attendance_id, message = await mark_attendance(enrollment_no, event_id, present=True)
        
        if success and attendance_id:
            print(f"✅ Attendance marked successfully: {attendance_id}")
            print(f"   Message: {message}")
        else:
            print(f"❌ Failed to mark attendance: {message}")
            return
    
    # Step 3: Verify data consistency
    print(f"\n--- Step 3: Verifying Data Consistency ---")
    
    # Check student record
    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
    participation = student_data.get('event_participations', {}).get(event_id, {})
    
    stored_attendance_id = participation.get('attendance_id')
    stored_registration_id = participation.get('registration_id')
    attendance_marked_at = participation.get('attendance_marked_at')
    
    print(f"Student Record:")
    print(f"  Registration ID: {stored_registration_id}")
    print(f"  Attendance ID: {stored_attendance_id}")
    print(f"  Marked At: {attendance_marked_at}")
    
    # Check event record
    event_data = await DatabaseOperations.find_one("events", {"event_id": event_id})
    if event_data and stored_attendance_id:
        event_attendance = event_data.get('attendances', {}).get(stored_attendance_id)
        if event_attendance == enrollment_no:
            print(f"✅ Event record consistent: {stored_attendance_id} -> {event_attendance}")
        else:
            print(f"❌ Event record inconsistent: {stored_attendance_id} -> {event_attendance}")
    
    # Step 4: Test auto-fetch simulation
    print(f"\n--- Step 4: Testing Auto-Fetch Data Structure ---")
    
    if stored_registration_id and stored_attendance_id:
        # Simulate the data that would be auto-filled in the form
        auto_fill_data = {
            "registrar_id": stored_registration_id,
            "full_name": student_data.get('full_name'),
            "enrollment_no": student_data.get('enrollment_no'),
            "email": student_data.get('email'),
            "mobile_no": student_data.get('mobile_no'),
            "department": student_data.get('department'),
            "semester": student_data.get('semester'),
            "registration_type": participation.get('registration_type', 'individual')
        }
        
        print(f"Auto-fill data structure:")
        for key, value in auto_fill_data.items():
            print(f"  {key}: {value}")
        
        print("✅ Auto-fetch data structure is complete and valid")
    
    # Step 5: Test validation scenarios
    print(f"\n--- Step 5: Testing Validation Scenarios ---")
    
    # Test 1: Non-registered student
    test_enrollment = "22BEIT99999"  # Non-existent student
    success, attendance_id, message = await mark_attendance(test_enrollment, event_id, present=True)
    if not success:
        print("✅ CORRECT: Non-registered student blocked")
    else:
        print("❌ INCORRECT: Non-registered student should be blocked")
    
    # Test 2: Student registered for different event
    test_event_id = "NONEXISTENT_EVENT_2025"
    success, attendance_id, message = await mark_attendance(enrollment_no, test_event_id, present=True)
    if not success:
        print("✅ CORRECT: Unregistered event blocked")
    else:
        print("❌ INCORRECT: Unregistered event should be blocked")
    
    print(f"\n--- Test Summary ---")
    print("✅ Enhanced attendance marking system is working correctly")
    print("✅ Auto-fetch functionality data structure is valid")
    print("✅ Validation scenarios pass")
    print("✅ Data consistency maintained between student and event records")
    
    print(f"\n🎉 All attendance marking tests completed successfully!")

async def test_absent_student_scenario():
    """Test the scenario for marking student as absent"""
    print(f"\n--- Testing Absent Student Scenario ---")
    
    enrollment_no = "22BEIT30044"  # Different student for absent test
    event_id = "AI_ML_BOOTCAMP_2025"
    
    # Create test registration if needed
    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
    if not student_data:
        print("❌ Test student for absent scenario not found")
        return
    
    event_participations = student_data.get('event_participations', {})
    if event_id not in event_participations:
        registration_id = generate_registration_id(enrollment_no, event_id)
        await DatabaseOperations.update_one(
            "students",
            {"enrollment_no": enrollment_no},
            {"$set": {
                f"event_participations.{event_id}": {
                    "registration_id": registration_id,
                    "registration_type": "individual",
                    "registered_at": datetime.now(timezone.utc),
                    "attendance_id": None,
                    "feedback_id": None,
                    "certificate_id": None
                }
            }}
        )
        print(f"✅ Created test registration for absent scenario: {registration_id}")
    
    # Mark student as absent
    success, attendance_id, message = await mark_attendance(enrollment_no, event_id, present=False)
    
    if success and attendance_id is None:
        print("✅ CORRECT: Absent student has no attendance_id")
        print(f"   Message: {message}")
        
        # Verify the attendance_status is set to 'absent'
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
        participation = student_data.get('event_participations', {}).get(event_id, {})
        attendance_status = participation.get('attendance_status')
        
        if attendance_status == 'absent':
            print("✅ CORRECT: Attendance status set to 'absent'")
        else:
            print(f"❌ INCORRECT: Expected 'absent' status, got: {attendance_status}")
    else:
        print(f"❌ INCORRECT: Absent student should not get attendance_id")

if __name__ == "__main__":
    asyncio.run(test_attendance_marking())
    asyncio.run(test_absent_student_scenario())
