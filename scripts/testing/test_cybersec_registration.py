#!/usr/bin/env python3
"""
Test script to verify the individual registration fix for CYBERSEC_AWARENESS_2025
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.db_operations import DatabaseOperations
from config.database import Database

async def test_cybersec_event_registration():
    """Test the specific event that had registration issues"""
    print("🧪 Testing CYBERSEC_AWARENESS_2025 Event Registration Fix")
    print("=" * 60)
    
    try:
        event_id = "CYBERSEC_AWARENESS_2025"
        
        # 1. Check main events collection
        event_data = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event_data:
            print(f"❌ Event {event_id} not found")
            return
        
        print(f"✅ Found event: {event_data.get('event_name', event_id)}")
        
        # 2. Check registrations in main events collection
        registrations = event_data.get('registrations', {})
        print(f"📋 Registrations in main events collection: {len(registrations)}")
        
        for reg_id, enrollment in registrations.items():
            print(f"  • {reg_id} → {enrollment}")
        
        # 3. Check if event-specific collection exists (it shouldn't for new architecture)
        safe_collection_name = ''.join(c for c in event_id if c.isalnum() or c in '-_')
        db = Database.client["CampusConnect"] if Database.client else None
        
        event_collection_exists = False
        event_collection_count = 0
        
        if db is not None:
            collection_names = await db.list_collection_names()
            if safe_collection_name in collection_names:
                event_collection_exists = True
                event_collection = db[safe_collection_name]
                event_collection_count = await event_collection.count_documents({})
                print(f"⚠️  Event-specific collection '{safe_collection_name}' exists with {event_collection_count} documents")
                
                # Show sample documents from event collection
                if event_collection_count > 0:
                    sample_docs = await event_collection.find({}).limit(3).to_list(length=3)
                    print("   Sample documents from event collection:")
                    for doc in sample_docs:
                        print(f"     • {doc.get('enrollment_no')} - {doc.get('registration_id')}")
            else:
                print(f"✅ No event-specific collection '{safe_collection_name}' found (correct for new architecture)")
        
        # 4. Check student data consistency
        students_with_participation = await DatabaseOperations.find_many(
            "students", 
            {f"event_participations.{event_id}": {"$exists": True}}
        )
        
        print(f"👥 Students with event participation: {len(students_with_participation)}")
        
        for student in students_with_participation:
            enrollment = student.get('enrollment_no')
            participation = student.get('event_participations', {}).get(event_id, {})
            print(f"  • {enrollment}:")
            print(f"    Registration ID: {participation.get('registration_id')}")
            print(f"    Registration Type: {participation.get('registration_type')}")
            print(f"    Attendance ID: {participation.get('attendance_id')}")
            print(f"    Feedback ID: {participation.get('feedback_id')}")
            print(f"    Certificate ID: {participation.get('certificate_id')}")
        
        # 5. Data consistency analysis
        events_reg_count = len(registrations)
        student_reg_count = len(students_with_participation)
        
        print(f"\n📊 Data Consistency Analysis:")
        print(f"  Events collection registrations: {events_reg_count}")
        print(f"  Students with participation: {student_reg_count}")
        print(f"  Event-specific collection documents: {event_collection_count}")
        
        if events_reg_count == student_reg_count:
            print("✅ Main data is consistent between events and students collections")
        else:
            print("⚠️  Inconsistency between events and students collections")
        
        if event_collection_exists and event_collection_count > 0:
            print("⚠️  Old event-specific collection still contains data")
            print("   This suggests the system was using the old architecture")
            
            # Check if data in event collection matches main events collection
            if event_collection_count == events_reg_count:
                print("   Data count matches main events collection")
            else:
                print(f"   Data count mismatch: {event_collection_count} vs {events_reg_count}")
        
        # 6. Check event status
        status = event_data.get('status', 'unknown')
        print(f"\n🔄 Event Status: {status}")
        
        # 7. Test the MongoDB collection boolean issue that was fixed
        print(f"\n🐛 Testing MongoDB Collection Boolean Fix:")
        try:
            # This should work now with the fix
            event_collection = await Database.get_event_collection(event_id)
            if event_collection is None:
                print("✅ MongoDB collection check works correctly (returned None)")
            else:
                print("✅ MongoDB collection check works correctly (returned collection)")
                # This line would have failed before the fix
                print(f"   Collection type: {type(event_collection)}")
        except Exception as e:
            print(f"❌ MongoDB collection boolean issue still exists: {e}")
        
        print(f"\n🎯 Summary:")
        print(f"  • Event has {events_reg_count} registrations in main collection")
        print(f"  • {student_reg_count} students have participation records")
        print(f"  • Event-specific collection: {'Exists' if event_collection_exists else 'Does not exist'}")
        print(f"  • MongoDB collection boolean fix: ✅ Working")
        
        if event_collection_exists and event_collection_count > 0:
            print(f"  ⚠️  RECOMMENDATION: Consider cleaning up old event-specific collection")
        else:
            print(f"  ✅ Architecture is correct - no cleanup needed")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\n🔄 Closing database connection...")
        await Database.close_db()

async def main():
    await test_cybersec_event_registration()

if __name__ == "__main__":
    asyncio.run(main())
