#!/usr/bin/env python3
"""
Migration script to convert existing events to the new data structure format.
This script will:
1. Add new required fields to existing events
2. Migrate old registration data to new format
3. Preserve existing data while adding new structure
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_operations import DatabaseOperations
from datetime import datetime


async def migrate_events_to_new_structure():
    """Migrate existing events to new data structure"""
    print("=== Event Data Structure Migration ===\n")
    
    try:        # Get all events
        events = await DatabaseOperations.find_many("events")
        print(f"Found {len(events)} events to migrate")
        
        migration_count = 0
        
        for event in events:
            event_id = event.get("event_id")
            print(f"\nMigrating event: {event_id}")
            
            # Prepare migration data
            migration_data = {}
            
            # Add new required fields if they don't exist
            if "is_paid" not in event:
                migration_data["is_paid"] = False
                
            if "is_team_based" not in event:
                migration_data["is_team_based"] = False
                
            if "registration_fee" not in event:
                migration_data["registration_fee"] = None
            
            # Initialize new data structure fields
            if "attendances" not in event:
                migration_data["attendances"] = {}
                
            if "team_attendances" not in event:
                migration_data["team_attendances"] = {}
                
            if "feedbacks" not in event:
                migration_data["feedbacks"] = {}
                
            if "team_feedbacks" not in event:
                migration_data["team_feedbacks"] = {}
                
            if "certificates" not in event:
                migration_data["certificates"] = {}
                
            if "team_certificates" not in event:
                migration_data["team_certificates"] = {}
            
            # Migrate old registrations format if needed
            old_registrations = event.get("registrations", {})
            if old_registrations and isinstance(list(old_registrations.values())[0], str):
                # Check if it's enrollment_no -> registration_id format (old)
                # vs registration_id -> enrollment_no format (new)
                sample_key = list(old_registrations.keys())[0]
                sample_value = old_registrations[sample_key]
                
                # If key looks like enrollment number, reverse the mapping
                if any(char.isdigit() for char in sample_key) and len(sample_key) > 10:
                    # This is old format: enrollment_no -> registration_id
                    new_registrations = {}
                    for enrollment_no, registration_id in old_registrations.items():
                        new_registrations[registration_id] = enrollment_no
                    
                    migration_data["registrations"] = new_registrations
                    print(f"   ✅ Migrated {len(new_registrations)} registrations")
            
            # Migrate old team registrations if needed
            old_team_registrations = event.get("team_registrations", {})
            if old_team_registrations:
                # Check if it's old TeamRegistration object format
                first_team = list(old_team_registrations.values())[0]
                if isinstance(first_team, dict) and "team_registration_id" in first_team:
                    # This is old format, need to convert
                    new_team_registrations = {}
                    
                    for team_reg_id, team_data in old_team_registrations.items():
                        team_name = team_data.get("team_name", f"Team_{team_reg_id}")
                        participants = team_data.get("participants", [])
                        leader = team_data.get("team_leader_enrollment")
                        
                        # Create new format
                        new_team_data = {}
                        
                        # Add leader if exists
                        if leader:
                            new_team_data[leader] = f"REG_LEADER_{leader[-4:]}"
                        
                        # Add participants  
                        for participant in participants:
                            new_team_data[participant] = f"REG_MEMBER_{participant[-4:]}"
                        
                        new_team_registrations[team_name] = new_team_data
                    
                    migration_data["team_registrations"] = new_team_registrations
                    print(f"   ✅ Migrated {len(new_team_registrations)} team registrations")
            
            # Apply migration if there's data to migrate
            if migration_data:
                result = await DatabaseOperations.update_one(
                    "events",
                    {"event_id": event_id},
                    {"$set": migration_data}
                )
                
                if result:
                    migration_count += 1
                    print(f"   ✅ Migration successful")
                else:
                    print(f"   ❌ Migration failed")
            else:
                print(f"   ℹ️  No migration needed")
        
        print(f"\n=== Migration Summary ===")
        print(f"Total events processed: {len(events)}")
        print(f"Events migrated: {migration_count}")
        print(f"Events skipped: {len(events) - migration_count}")
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()


async def migrate_students_to_new_structure():
    """Migrate existing student event participations to new structure"""
    print("\n=== Student Data Structure Migration ===\n")
    
    try:        # Get all students
        students = await DatabaseOperations.find_many("students")
        print(f"Found {len(students)} students to check")
        
        migration_count = 0
        
        for student in students:
            enrollment_no = student.get("enrollment_no")
            event_participations = student.get("event_participations", {})
            
            if not event_participations:
                continue
                
            needs_migration = False
            migration_data = {}
            
            for event_id, participation in event_participations.items():
                updated_participation = participation.copy()
                
                # Add new fields if missing
                if "payment_id" not in participation:
                    updated_participation["payment_id"] = None
                    needs_migration = True
                    
                if "payment_status" not in participation:
                    updated_participation["payment_status"] = None
                    needs_migration = True
                
                # Update registration type if using old values
                reg_type = participation.get("registration_type")
                if reg_type in ["team_leader", "team_participant"]:
                    updated_participation["registration_type"] = "team_member"
                    needs_migration = True
                
                # Convert team_registration_id to team_name
                if "team_registration_id" in participation:
                    # For now, use team_registration_id as team_name
                    # In a real migration, you'd look up the actual team name
                    updated_participation["team_name"] = participation["team_registration_id"]
                    del updated_participation["team_registration_id"]
                    needs_migration = True
                
                if needs_migration:
                    migration_data[f"event_participations.{event_id}"] = updated_participation
            
            # Apply migration if needed
            if migration_data:
                result = await DatabaseOperations.update_one(
                    "students",
                    {"enrollment_no": enrollment_no},
                    {"$set": migration_data}
                )
                
                if result:
                    migration_count += 1
                    print(f"   ✅ Migrated student: {enrollment_no}")
                else:
                    print(f"   ❌ Failed to migrate student: {enrollment_no}")
        
        print(f"\n=== Student Migration Summary ===")
        print(f"Total students processed: {len(students)}")
        print(f"Students migrated: {migration_count}")
        
    except Exception as e:
        print(f"❌ Student migration error: {e}")
        import traceback
        traceback.print_exc()


async def create_sample_event_configurations():
    """Create sample events with the new data structure"""
    print("\n=== Creating Sample Event Configurations ===\n")
    
    sample_events = [
        {
            "event_id": "SAMPLE_INDIVIDUAL_FREE_2025",
            "event_name": "Sample Individual Free Workshop",
            "event_type": "workshop",
            "organizing_department": "Information Technology",
            "short_description": "Sample individual free event",
            "start_datetime": datetime(2025, 7, 1, 10, 0),
            "end_datetime": datetime(2025, 7, 1, 17, 0),
            "venue": "Seminar Hall",
            "mode": "offline",
            "is_paid": False,
            "is_team_based": False,
            "published": True,
            "registrations": {},
            "attendances": {},
            "feedbacks": {},
            "certificates": {}
        },
        {
            "event_id": "SAMPLE_INDIVIDUAL_PAID_2025",
            "event_name": "Sample Individual Paid Certification",
            "event_type": "certification",
            "organizing_department": "Information Technology",
            "short_description": "Sample individual paid event",
            "start_datetime": datetime(2025, 7, 15, 10, 0),
            "end_datetime": datetime(2025, 7, 15, 17, 0),
            "venue": "Computer Lab",
            "mode": "offline",
            "is_paid": True,
            "is_team_based": False,
            "registration_fee": 299.0,
            "published": True,
            "registrations": {},
            "attendances": {},
            "feedbacks": {},
            "certificates": {}
        },
        {
            "event_id": "SAMPLE_TEAM_FREE_2025",
            "event_name": "Sample Team Free Hackathon",
            "event_type": "hackathon",
            "organizing_department": "Information Technology",
            "short_description": "Sample team-based free event",
            "start_datetime": datetime(2025, 8, 1, 9, 0),
            "end_datetime": datetime(2025, 8, 2, 18, 0),
            "venue": "Innovation Lab",
            "mode": "offline",
            "is_paid": False,
            "is_team_based": True,
            "published": True,
            "team_registrations": {},
            "team_attendances": {},
            "team_feedbacks": {},
            "team_certificates": {}
        },
        {
            "event_id": "SAMPLE_TEAM_PAID_2025",
            "event_name": "Sample Team Paid Competition",
            "event_type": "competition",
            "organizing_department": "Information Technology",
            "short_description": "Sample team-based paid event",
            "start_datetime": datetime(2025, 8, 15, 9, 0),
            "end_datetime": datetime(2025, 8, 16, 18, 0),
            "venue": "Main Auditorium",
            "mode": "offline",
            "is_paid": True,
            "is_team_based": True,
            "registration_fee": 500.0,
            "published": True,
            "team_registrations": {},
            "team_attendances": {},
            "team_feedbacks": {},
            "team_certificates": {}
        }
    ]
    
    for event_data in sample_events:
        # Check if event already exists
        existing = await DatabaseOperations.find_one("events", {"event_id": event_data["event_id"]})
        
        if not existing:
            result = await DatabaseOperations.insert_one("events", event_data)
            if result:
                print(f"   ✅ Created sample event: {event_data['event_id']}")
            else:
                print(f"   ❌ Failed to create: {event_data['event_id']}")
        else:
            print(f"   ℹ️  Sample event already exists: {event_data['event_id']}")


async def main():
    """Run the complete migration"""
    print("🚀 Event Data Structure Migration Tool\n")
    print("This tool will migrate your existing events and students")
    print("to support the new data structure for:")
    print("- Team-based events with payment tracking")
    print("- Individual events with payment tracking")
    print("- Proper separation of attendance, feedback, and certificates")
    print("\n" + "="*60 + "\n")
    
    try:
        await migrate_events_to_new_structure()
        await migrate_students_to_new_structure()
        await create_sample_event_configurations()
        
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Test the new data structure with demo_event_data_structures.py")
        print("2. Update your application code to use the new EventDataManager")
        print("3. Verify that existing functionality still works")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
