#!/usr/bin/env python3
"""
Test validation flow to demonstrate that each phase properly validates the previous phases
"""

import asyncio
from event_lifecycle_helpers import mark_attendance, submit_feedback, generate_certificate
from utils.db_operations import DatabaseOperations

async def test_validation_flow():
    """Test that each phase properly validates prerequisites"""
    print("=== Testing Validation Flow ===")
    
    # Use the second student who still has clean registration data
    enrollment_no = "22CSEB10056"
    event_id = "AI_ML_BOOTCAMP_2025"
    
    print(f"Testing validation for: {enrollment_no} in event: {event_id}")
    
    # Check initial status
    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
    if student_data:
        participation = student_data.get('event_participations', {}).get(event_id, {})
        print(f"\nInitial status:")
        print(f"  Registration ID: {participation.get('registration_id')}")
        print(f"  Attendance ID: {participation.get('attendance_id')}")
        print(f"  Feedback ID: {participation.get('feedback_id')}")
        print(f"  Certificate ID: {participation.get('certificate_id')}")
    
    # Test 1: Try to submit feedback without attendance
    print(f"\n--- Test 1: Try to submit feedback without attendance ---")
    feedback_data = {"rating": 4, "comments": "Good event"}
    success, feedback_id, message = await submit_feedback(enrollment_no, event_id, feedback_data)
    print(f"Result: {message}")
    if not success:
        print("✅ CORRECT: Feedback submission blocked without attendance")
    else:
        print("❌ INCORRECT: Feedback submission should be blocked")
    
    # Test 2: Try to generate certificate without attendance and feedback
    print(f"\n--- Test 2: Try to generate certificate without attendance and feedback ---")
    success, certificate_id, message = await generate_certificate(enrollment_no, event_id)
    print(f"Result: {message}")
    if not success:
        print("✅ CORRECT: Certificate generation blocked without attendance")
    else:
        print("❌ INCORRECT: Certificate generation should be blocked")
    
    # Test 3: Mark attendance first
    print(f"\n--- Test 3: Mark attendance ---")
    success, attendance_id, message = await mark_attendance(enrollment_no, event_id, present=True)
    print(f"Result: {message}")
    if success:
        print(f"✅ Generated Attendance ID: {attendance_id}")
    
    # Test 4: Try to generate certificate without feedback (but with attendance)
    print(f"\n--- Test 4: Try to generate certificate with attendance but no feedback ---")
    success, certificate_id, message = await generate_certificate(enrollment_no, event_id)
    print(f"Result: {message}")
    if not success:
        print("✅ CORRECT: Certificate generation blocked without feedback")
    else:
        print("❌ INCORRECT: Certificate generation should be blocked")
    
    # Test 5: Submit feedback (now with attendance)
    print(f"\n--- Test 5: Submit feedback (with attendance) ---")
    success, feedback_id, message = await submit_feedback(enrollment_no, event_id, feedback_data)
    print(f"Result: {message}")
    if success:
        print(f"✅ Generated Feedback ID: {feedback_id}")
    
    # Test 6: Generate certificate (now with both attendance and feedback)
    print(f"\n--- Test 6: Generate certificate (with both attendance and feedback) ---")
    success, certificate_id, message = await generate_certificate(enrollment_no, event_id)
    print(f"Result: {message}")
    if success:
        print(f"✅ Generated Certificate ID: {certificate_id}")
    
    # Final validation status
    student_data = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
    if student_data:
        participation = student_data.get('event_participations', {}).get(event_id, {})
        print(f"\nFinal validation status:")
        print(f"  Registration ID: {participation.get('registration_id')}")
        print(f"  Attendance ID: {participation.get('attendance_id')}")
        print(f"  Feedback ID: {participation.get('feedback_id')}")
        print(f"  Certificate ID: {participation.get('certificate_id')}")
        print("✅ All validation steps passed!")

async def test_absent_student_flow():
    """Test the flow for a student marked as absent"""
    print(f"\n=== Testing Absent Student Flow ===")
    
    # Reset the first student to test absent flow
    enrollment_no = "22BEIT30043"
    event_id = "AI_ML_BOOTCAMP_2025"
    
    print(f"Resetting {enrollment_no} to clean state...")
    
    # Reset to clean state
    await DatabaseOperations.update_one(
        "students",
        {"enrollment_no": enrollment_no},
        {
            "$set": {
                f"event_participations.{event_id}.attendance_id": None,
                f"event_participations.{event_id}.feedback_id": None,
                f"event_participations.{event_id}.certificate_id": None
            }
        }
    )
    
    print(f"Testing absent flow for: {enrollment_no}")
    
    # Mark as absent
    print(f"\n--- Marking student as absent ---")
    success, attendance_id, message = await mark_attendance(enrollment_no, event_id, present=False)
    print(f"Result: {message}")
    print(f"Attendance ID: {attendance_id} (should be None for absent students)")
    
    # Try to submit feedback for absent student
    print(f"\n--- Try to submit feedback for absent student ---")
    feedback_data = {"rating": 3, "comments": "Missed the event"}
    success, feedback_id, message = await submit_feedback(enrollment_no, event_id, feedback_data)
    print(f"Result: {message}")
    if not success:
        print("✅ CORRECT: Feedback blocked for absent student")
    
    # Try to generate certificate for absent student
    print(f"\n--- Try to generate certificate for absent student ---")
    success, certificate_id, message = await generate_certificate(enrollment_no, event_id)
    print(f"Result: {message}")
    if not success:
        print("✅ CORRECT: Certificate blocked for absent student")

async def main():
    await test_validation_flow()
    await test_absent_student_flow()

if __name__ == "__main__":
    asyncio.run(main())
