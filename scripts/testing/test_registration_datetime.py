#!/usr/bin/env python3
"""Test script to check registration datetime data structure"""

import asyncio
import sys
import os
from datetime import datetime

# Add the admin directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db_operations import DatabaseOperations
from config.database import Database

async def test_registration_datetime():
    """Test registration datetime data structure"""
    print("=== Testing Registration DateTime Structure ===")
    try:
        # Connect to database
        await Database.connect_db()
        print("✅ Connected to database")
        
        # Find students with event participations
        students = await DatabaseOperations.find_many(
            "students", 
            {"event_participations": {"$exists": True, "$ne": {}}},
            limit=5
        )
        
        print(f"\nFound {len(students)} students with registrations")
        
        for student in students:
            enrollment = student.get('enrollment_no', 'Unknown')
            name = student.get('full_name', 'Unknown')
            participations = student.get('event_participations', {})
            
            print(f"\n📋 Student: {enrollment} - {name}")
            
            for event_id, participation in participations.items():
                reg_datetime = participation.get('registration_datetime')
                reg_type = participation.get('registration_type', 'unknown')
                reg_id = participation.get('registration_id', 'N/A')
                
                print(f"  Event: {event_id}")
                print(f"  Registration Type: {reg_type}")
                print(f"  Registration ID: {reg_id}")
                print(f"  Registration DateTime: {reg_datetime}")
                print(f"  DateTime Type: {type(reg_datetime)}")
                
                if reg_datetime:
                    if isinstance(reg_datetime, datetime):
                        formatted = reg_datetime.strftime('%d %B %Y at %I:%M %p')
                        print(f"  ✅ Formatted: {formatted}")
                    elif isinstance(reg_datetime, str):
                        try:
                            parsed_dt = datetime.fromisoformat(reg_datetime.replace('Z', '+00:00'))
                            formatted = parsed_dt.strftime('%d %B %Y at %I:%M %p')
                            print(f"  ✅ Parsed & Formatted: {formatted}")
                        except Exception as e:
                            print(f"  ❌ String parsing failed: {e}")
                    else:
                        print(f"  ⚠️  Unknown datetime type: {type(reg_datetime)}")
                else:
                    print(f"  ❌ No registration datetime found")
                
                print("  " + "-" * 40)
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await Database.close_db()

if __name__ == "__main__":
    asyncio.run(test_registration_datetime())
