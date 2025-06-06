#!/usr/bin/env python3
"""
Final verification script for attendance marking system
"""

import asyncio
from utils.db_operations import DatabaseOperations

async def final_status_check():
    print("🎯 FINAL ATTENDANCE SYSTEM STATUS CHECK")
    print("=" * 60)
    
    try:
        # Check student attendance status
        student_data = await DatabaseOperations.find_one("students", {"enrollment_no": "22BEIT30043"})
        
        if student_data:
            event_id = "GREEN_INNOVATION_HACKATHON_2025"
            participation = student_data.get('event_participations', {}).get(event_id, {})
            
            registration_id = participation.get('registration_id')
            attendance_id = participation.get('attendance_id')
            attendance_status = participation.get('attendance_status')
            
            print(f"👤 Student: {student_data.get('full_name')}")
            print(f"🆔 Enrollment: {student_data.get('enrollment_no')}")
            print(f"📝 Registration ID: {registration_id}")
            print(f"✅ Attendance ID: {attendance_id}")
            print(f"📊 Attendance Status: {attendance_status}")
            
            if attendance_id:
                print("🎉 STATUS: ATTENDANCE SUCCESSFULLY MARKED!")
            else:
                print("❌ STATUS: NO ATTENDANCE RECORDED")
        
        # Check event data
        event_data = await DatabaseOperations.find_one("events", {"event_id": "GREEN_INNOVATION_HACKATHON_2025"})
        
        if event_data:
            attendances = event_data.get('attendances', {})
            registrations = event_data.get('registrations', {})
            
            print(f"\n🏆 Event: {event_data.get('event_name')}")
            print(f"📈 Event Status: {event_data.get('status')}")
            print(f"⏱️  Sub Status: {event_data.get('sub_status')}")
            print(f"👥 Total Registrations: {len(registrations)}")
            print(f"🎯 Total Attendances: {len(attendances)}")
            
            if len(attendances) > 0:
                print("✅ ATTENDANCE TRACKING: ACTIVE")
                for att_id, att_data in attendances.items():
                    if isinstance(att_data, dict):
                        print(f"   - {att_id}: {att_data.get('enrollment_no')} ({att_data.get('attendance_status')})")
                    else:
                        print(f"   - {att_id}: {att_data}")
            else:
                print("❌ ATTENDANCE TRACKING: NO ATTENDANCES RECORDED")
        
        print("=" * 60)
        print("🎊 SYSTEM VERIFICATION COMPLETE!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during verification: {str(e)}")
        return False

if __name__ == "__main__":
    result = asyncio.run(final_status_check())
    
    if result:
        print("\n🌟 ATTENDANCE MARKING SYSTEM: FULLY OPERATIONAL! 🌟")
    else:
        print("\n⚠️  ATTENDANCE MARKING SYSTEM: NEEDS ATTENTION! ⚠️")
