#!/usr/bin/env python3
"""
Clean up existing registrations to follow the correct flow
Set attendance_id, feedback_id, and certificate_id to None for existing registrations
"""

import asyncio
from typing import Dict, Optional, List
from utils.db_operations import DatabaseOperations

async def cleanup_existing_registrations():
    print("=== Cleaning Up Existing Registrations ===")
    
    try:
        # Get all students with registrations
        students = await DatabaseOperations.find_many("students", {})
        
        updated_count = 0
        
        for student in students:
            enrollment = student.get('enrollment_no', 'Unknown')
            participations = student.get('event_participations', {})
            
            if participations:
                print(f"\nProcessing student: {enrollment}")
                
                for event_id, participation in participations.items():
                    registration_id = participation.get('registration_id')
                    attendance_id = participation.get('attendance_id')
                    feedback_id = participation.get('feedback_id')
                    certificate_id = participation.get('certificate_id')
                    
                    # Check if cleanup is needed
                    if registration_id and (attendance_id or feedback_id or certificate_id):
                        print(f"  Event: {event_id} - Needs cleanup")
                        
                        # Update the participation to set other IDs to None
                        update_result = await DatabaseOperations.update_one(
                            "students",
                            {"enrollment_no": enrollment},
                            {
                                "$set": {
                                    f"event_participations.{event_id}.attendance_id": None,
                                    f"event_participations.{event_id}.feedback_id": None,
                                    f"event_participations.{event_id}.certificate_id": None
                                }
                            }
                        )
                        
                        if update_result:
                            print(f"    ✅ Updated - Set attendance_id, feedback_id, certificate_id to None")
                            updated_count += 1
                        else:
                            print(f"    ❌ Failed to update")
                    else:
                        print(f"  Event: {event_id} - Already correct")
        
        print(f"\n=== Cleanup Complete ===")
        print(f"Updated {updated_count} registrations")
        
    except Exception as e:
        print(f"Error: {e}")

async def verify_cleanup():
    print("\n=== Verifying Cleanup Results ===")
    
    try:
        students = await DatabaseOperations.find_many("students", {})
        
        for student in students:
            enrollment = student.get('enrollment_no', 'Unknown')
            participations = student.get('event_participations', {})
            
            if participations:
                print(f"\nStudent: {enrollment}")
                
                for event_id, participation in participations.items():
                    registration_id = participation.get('registration_id')
                    attendance_id = participation.get('attendance_id')
                    feedback_id = participation.get('feedback_id')
                    certificate_id = participation.get('certificate_id')
                    
                    print(f"  Event: {event_id}")
                    print(f"    Registration ID: {registration_id}")
                    print(f"    Attendance ID: {attendance_id}")
                    print(f"    Feedback ID: {feedback_id}")
                    print(f"    Certificate ID: {certificate_id}")
                    
                    if registration_id and attendance_id is None and feedback_id is None and certificate_id is None:
                        print("    ✅ CORRECT: Only registration_id set")
                    else:
                        print("    ❌ Still incorrect")
                        
    except Exception as e:
        print(f"Error: {e}")

async def main():
    await cleanup_existing_registrations()
    await verify_cleanup()

if __name__ == "__main__":
    asyncio.run(main())
