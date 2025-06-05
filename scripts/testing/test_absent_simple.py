#!/usr/bin/env python3
"""
Simple test for absent student scenario in attendance marking system.
"""

import asyncio
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from utils.db_operations import DatabaseOperations
from utils.event_lifecycle_helpers import mark_attendance

async def test_absent_student():
    """Test marking a student as absent"""
    print("🧪 Testing Absent Student Scenario")
    print("=" * 40)
    
    try:
        # Test data
        enrollment_no = "22BEIT30043"  # Known test student
        event_id = "AI_ML_BO"  # Known test event
        
        # Test marking as absent
        print(f"\nTesting absent marking for {enrollment_no}...")
        success, result_id, message = await mark_attendance(
            enrollment_no=enrollment_no,
            event_id=event_id,
            present=False  # Mark as absent
        )
        
        if success:
            print(f"✅ Absent status marked successfully")
            print(f"   Result: {result_id}")
            print(f"   Message: {message}")
        else:
            print(f"ℹ️  Expected result: {message}")
            if "already marked" in message.lower():
                print("✅ Duplicate attendance prevention working correctly")
        
        print("\n🎉 Absent scenario test completed!")
        
    except Exception as e:
        print(f"❌ Error during absent test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_absent_student())
