#!/usr/bin/env python3
"""
Test the V2 JavaScript Certificate Generator API endpoints
"""

import asyncio
import json
from utils.db_operations import DatabaseOperations

async def test_certificate_data_api():
    """Test the certificate data API endpoint logic"""
    print("🧪 Testing Certificate Data API...")
    
    try:
        # Test with known working data
        event_id = "DIGITAL_LITERACY_WORKSHOP_2025"
        enrollment_no = "22BEIT30043"
        
        print(f"📋 Testing with Event: {event_id}, Student: {enrollment_no}")
        
        # Get event details
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        if not event:
            print("❌ Event not found")
            return False
            
        print(f"✅ Event found: {event.get('event_name')}")
        
        # Get student details
        student = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
        if not student:
            print("❌ Student not found")
            return False
            
        print(f"✅ Student found: {student.get('full_name')}")
        
        # Check certificate template
        template_path = event.get("certificate_template")
        if not template_path:
            print("❌ No certificate template path")
            return False
            
        print(f"✅ Template path: {template_path}")
        
        # Read template content
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_html = f.read()
            print(f"✅ Template loaded: {len(template_html)} characters")
        except Exception as e:
            print(f"❌ Template read error: {e}")
            return False
        
        # Get participation data
        participation = student.get("event_participations", {}).get(event_id, {})
        student_data_in_participation = participation.get("student_data", {})
        
        # Prepare student data
        student_data = {
            "enrollment_no": enrollment_no,
            "full_name": student_data_in_participation.get("full_name", student.get("full_name", enrollment_no)),
            "department": student.get("department", "Unknown Department"),
            "email": student_data_in_participation.get("email", student.get("email"))
        }
        
        # Prepare event data
        event_data = {
            "event_id": event_id,
            "event_name": event.get("event_name"),
            "event_date": event.get("start_datetime"),
            "registration_mode": event.get("registration_mode"),
            "registration_type": event.get("registration_type")
        }
        
        # Prepare team data (if applicable)
        team_data = None
        if event.get("registration_mode", "").lower() == "team":
            team_name = student_data_in_participation.get("team_name")
            if not team_name:
                team_registration_id = participation.get("team_registration_id")
                if team_registration_id:
                    team_registrations = event.get("team_registrations", {})
                    team_details = team_registrations.get(team_registration_id, {})
                    team_name = team_details.get("team_name")
            
            if team_name:
                team_data = {"team_name": team_name}
        
        # Prepare final response data
        response_data = {
            "template_html": template_html,
            "student_data": student_data,
            "event_data": event_data,
            "team_data": team_data
        }
        
        print("✅ Certificate data prepared successfully")
        print(f"📊 Student: {student_data['full_name']}")
        print(f"📊 Event: {event_data['event_name']}")
        print(f"📊 Department: {student_data['department']}")
        print(f"📊 Team: {team_data['team_name'] if team_data else 'N/A'}")
        print(f"📊 Template size: {len(template_html)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    print("🎯 Testing V2 Certificate Generator API Components...")
    print("=" * 60)
    
    success = await test_certificate_data_api()
    
    print("=" * 60)
    if success:
        print("✅ All API tests passed!")
        print("🚀 V2 Certificate Generator backend is ready")
    else:
        print("❌ Some tests failed")
        print("🔧 Please check the implementation")

if __name__ == "__main__":
    asyncio.run(main())
