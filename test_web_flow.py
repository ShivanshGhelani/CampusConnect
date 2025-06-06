#!/usr/bin/env python3
"""
Test script to simulate the web attendance marking flow
"""

import asyncio
import aiohttp
from datetime import datetime

async def test_web_attendance_flow():
    """Test the complete web attendance marking flow"""
    
    base_url = "http://localhost:8000"
    
    # Student credentials
    enrollment_no = "22BEIT30043"
    password = "Shiv@2808"
    event_id = "GREEN_INNOVATION_HACKATHON_2025"
    
    print(f"Testing web attendance flow for {enrollment_no}")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Login
            print("1. Testing login...")
            login_data = {
                "enrollment_no": enrollment_no,
                "password": password
            }
            
            async with session.post(f"{base_url}/client/login", data=login_data) as response:
                if response.status == 200:
                    print("   ✓ Login successful")
                else:
                    print(f"   ✗ Login failed with status {response.status}")
                    return
            
            # 2. Access attendance marking page
            print("2. Testing attendance marking page access...")
            async with session.get(f"{base_url}/client/events/{event_id}/mark-attendance") as response:
                if response.status == 200:
                    content = await response.text()
                    if "mark attendance" in content.lower() or "attendance marking" in content.lower():
                        print("   ✓ Attendance marking page accessible")
                    else:
                        print("   ⚠ Page accessible but content unclear")
                        print(f"   Response length: {len(content)} characters")
                else:
                    print(f"   ✗ Attendance page failed with status {response.status}")
                    response_text = await response.text()
                    if "You must be registered" in response_text:
                        print("   ✗ Registration validation failed")
                    elif "not available during" in response_text:
                        print("   ✗ Event timing validation failed")
                    else:
                        print(f"   Response preview: {response_text[:200]}...")
            
            # 3. Test attendance submission (if attendance not already marked)
            print("3. Testing attendance submission...")
            
            # First, let's check if attendance is already marked by looking at the page content
            async with session.get(f"{base_url}/client/events/{event_id}/mark-attendance") as response:
                content = await response.text()
                if "already marked" in content.lower():
                    print("   ✓ Attendance already marked (expected from previous test)")
                    return
            
            # If not marked, try to submit attendance
            attendance_data = {
                "student_name": "Shivansh Ghelani",
                "registration_id": "REG_GREEN_IN_30043_1076"
            }
            
            async with session.post(f"{base_url}/client/events/{event_id}/mark-attendance", data=attendance_data) as response:
                if response.status == 200:
                    content = await response.text()
                    if "success" in content.lower() or "marked" in content.lower():
                        print("   ✓ Attendance submission successful")
                    else:
                        print("   ⚠ Submission completed but result unclear")
                else:
                    print(f"   ✗ Attendance submission failed with status {response.status}")
                    response_text = await response.text()
                    print(f"   Error response: {response_text[:300]}...")
        
        except Exception as e:
            print(f"   ✗ Error during web flow test: {str(e)}")
    
    print("=" * 60)
    print("Web flow test completed!")

if __name__ == "__main__":
    asyncio.run(test_web_attendance_flow())
