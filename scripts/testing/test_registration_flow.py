#!/usr/bin/env python3
"""
Test script to verify the corrected registration flow
Only registration_id should be generated during registration phase
"""

import asyncio
from typing import Dict, Optional, List
from utils.db_operations import DatabaseOperations

async def test_registration_flow():
    print("=== Testing Corrected Registration Flow ===")
    
    try:
        # Check current registrations
        students = await DatabaseOperations.find_many("students", {})
        
        print(f"Found {len(students)} students")
        
        for student in students:
            enrollment = student.get('enrollment_no', 'Unknown')
            participations = student.get('event_participations', {})
            
            if participations:
                print(f"\nStudent: {enrollment}")
                
                for event_id, participation in participations.items():
                    print(f"  Event: {event_id}")
                    print(f"  Registration Type: {participation.get('registration_type', 'Unknown')}")
                    
                    # Check if only registration_id is set and others are None
                    registration_id = participation.get('registration_id')
                    attendance_id = participation.get('attendance_id')
                    feedback_id = participation.get('feedback_id')
                    certificate_id = participation.get('certificate_id')
                    
                    print(f"  Registration ID: {registration_id}")
                    print(f"  Attendance ID: {attendance_id}")
                    print(f"  Feedback ID: {feedback_id}")
                    print(f"  Certificate ID: {certificate_id}")
                    
                    # Verify correct flow
                    if registration_id and attendance_id is None and feedback_id is None and certificate_id is None:
                        print("  ✅ CORRECT: Only registration_id set, others are None")
                    elif registration_id and (attendance_id or feedback_id or certificate_id):
                        print("  ❌ INCORRECT: Other IDs should be None during registration phase")
                    else:
                        print("  ⚠️  MISSING: Registration ID not found")
                    
                    # Check team registration ID if applicable
                    team_registration_id = participation.get('team_registration_id')
                    if team_registration_id:
                        print(f"  Team Registration ID: {team_registration_id}")
                        
    except Exception as e:
        print(f"Error: {e}")

async def show_correct_flow():
    print("\n=== CORRECT EVENT LIFECYCLE FLOW ===")
    print("1. REGISTRATION PHASE:")
    print("   - Generate: registration_id")
    print("   - Set to None: attendance_id, feedback_id, certificate_id")
    print("   - Purpose: Identify registered participants")
    
    print("\n2. ATTENDANCE MARKING PHASE:")
    print("   - Use: registration_id (to validate participant is registered)")
    print("   - Generate: attendance_id (only if participant is present)")
    print("   - Purpose: Track event attendance")
    
    print("\n3. FEEDBACK SUBMISSION PHASE:")
    print("   - Use: registration_id + attendance_id (to validate participant attended)")
    print("   - Generate: feedback_id (only if feedback is submitted)")
    print("   - Purpose: Collect event feedback")
    
    print("\n4. CERTIFICATE GENERATION PHASE:")
    print("   - Use: feedback_id (to validate participant provided feedback)")
    print("   - Generate: certificate_id (only if certificate is issued)")
    print("   - Purpose: Issue completion certificates")

async def main():
    await show_correct_flow()
    await test_registration_flow()

if __name__ == "__main__":
    asyncio.run(main())
