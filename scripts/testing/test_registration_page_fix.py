#!/usr/bin/env python3
"""
Test script to verify that the existing registration page now properly displays
registration dates and team information after our fixes.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils.db_operations import DatabaseOperations
from config.database import Database
from routes.client.event_registration import (
    get_registration_datetime_from_team_data,
    get_team_info_for_registration,
)


async def test_registration_datetime_fix():
    """Test that our helper function properly retrieves registration datetimes"""
    print("=== Testing Registration DateTime Fix ===")

    try:
        # Connect to database
        await Database.connect_db()
        print("✅ Connected to database")

        # Find a student with team registrations
        student_enrollment = "22BEIT30043"  # Known to have team registrations
        student_data = await DatabaseOperations.find_one(
            "students", {"enrollment_no": student_enrollment}
        )

        if not student_data:
            print(f"❌ Student {student_enrollment} not found")
            return

        print(
            f"👤 Testing with student: {student_data.get('full_name')} ({student_enrollment})"
        )

        # Get their event participations
        event_participations = student_data.get("event_participations", {})

        for event_id, participation in event_participations.items():
            print(f"\n📅 Event: {event_id}")
            print(f"   Registration Type: {participation.get('registration_type')}")
            print(
                f"   Team Registration ID: {participation.get('team_registration_id')}"
            )
            print(
                f"   Participation DateTime (old): {participation.get('registration_datetime')}"
            )

            # Get the event data
            event = await DatabaseOperations.find_one("events", {"event_id": event_id})
            if not event:
                print(f"   ❌ Event not found")
                continue

            # Test our helper function
            actual_datetime = await get_registration_datetime_from_team_data(
                event, participation
            )
            print(f"   🎯 Actual Registration DateTime: {actual_datetime}")

            if actual_datetime:
                if isinstance(actual_datetime, datetime):
                    formatted_date = actual_datetime.strftime("%d %B %Y")
                    print(f"   ✅ Formatted Date: {formatted_date}")
                else:
                    print(
                        f"   ⚠️  Datetime is not a datetime object: {type(actual_datetime)}"
                    )
            else:
                print(f"   ❌ No registration datetime found")

            # Test team info function
            team_info = await get_team_info_for_registration(event, participation)
            print(f"   👥 Team Info: {team_info}")

            print("   " + "-" * 50)

        print("\n=== Test Registration Data Building ===")

        # Simulate what happens in the route
        for event_id, participation in event_participations.items():
            event = await DatabaseOperations.find_one("events", {"event_id": event_id})
            if not event:
                continue

            print(f"\n📋 Building registration data for {event_id}")

            # Get actual registration datetime (our fix)
            actual_registration_datetime = (
                await get_registration_datetime_from_team_data(event, participation)
            )

            # Get team information
            team_info = await get_team_info_for_registration(event, participation)

            # Build registration data (as in routes)
            registration_data = {
                "registrar_id": participation.get("registration_id"),
                "registration_type": participation.get(
                    "registration_type", "individual"
                ),
                "registration_datetime": actual_registration_datetime,
                "payment_status": participation.get("payment_status", "pending"),
                "payment_completed_datetime": participation.get(
                    "payment_completed_datetime"
                ),
                # Student data from registration
                "full_name": participation.get("student_data", {}).get(
                    "full_name", student_data.get("full_name")
                ),
                "enrollment_no": student_enrollment,
                "department": participation.get("student_data", {}).get(
                    "department", student_data.get("department")
                ),
                "semester": participation.get("student_data", {}).get(
                    "semester", student_data.get("semester")
                ),
            }

            print(f"   📝 Registration Data:")
            for key, value in registration_data.items():
                if key == "registration_datetime" and value:
                    formatted_val = (
                        value.strftime("%d %B %Y")
                        if isinstance(value, datetime)
                        else value
                    )
                    print(f"      {key}: {value} -> {formatted_val}")
                else:
                    print(f"      {key}: {value}")

            print(f"   👥 Team Info:")
            if team_info:
                for key, value in team_info.items():
                    print(f"      {key}: {value}")
            else:
                print(f"      None (Individual registration)")

            print("   " + "=" * 50)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await Database.close_db()
        print("🔌 Closed database connection")


if __name__ == "__main__":
    asyncio.run(test_registration_datetime_fix())
