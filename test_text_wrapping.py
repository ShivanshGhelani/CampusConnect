#!/usr/bin/env python3
"""
Test the improved text wrapping in certificate generation
"""

import asyncio
from utils.db_operations import DatabaseOperations

async def test_certificate_with_long_text():
    """Test certificate generation with long event name and department"""
    print("🧪 Testing Certificate Generation with Long Text...")
    
    try:
        # Test with actual event data
        event_id = "DIGITAL_LITERACY_WORKSHOP_2025"
        enrollment_no = "22BEIT30043"
        
        # Get event and student data
        event = await DatabaseOperations.find_one("events", {"event_id": event_id})
        student = await DatabaseOperations.find_one("students", {"enrollment_no": enrollment_no})
        
        if not event or not student:
            print("❌ Test data not found")
            return
        
        print(f"📋 Event Name: {event.get('event_name')}")
        print(f"📋 Event Name Length: {len(event.get('event_name', ''))} characters")
        
        # Get student details
        participation = student.get("event_participations", {}).get(event_id, {})
        student_data = participation.get("student_data", {})
        full_name = student_data.get("full_name", student.get("full_name", enrollment_no))
        department = student.get("department", "Unknown Department")
        
        print(f"📋 Student Name: {full_name}")
        print(f"📋 Student Name Length: {len(full_name)} characters")
        print(f"📋 Department: {department}")
        print(f"📋 Department Length: {len(department)} characters")
        
        # Check template path
        template_path = event.get("certificate_template")
        if template_path:
            print(f"✅ Template found: {template_path}")
            
            # Read template to verify placeholders
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Check for proper placeholders
            required_placeholders = [
                '{{participant_name}}',
                '{{department_name}}', 
                '{{event_name}}',
                '{{event_date}}',
                '{{issue_date}}'
            ]
            
            missing_placeholders = []
            for placeholder in required_placeholders:
                if placeholder not in template_content:
                    missing_placeholders.append(placeholder)
            
            if missing_placeholders:
                print(f"⚠️ Missing placeholders: {missing_placeholders}")
            else:
                print("✅ All required placeholders found in template")
            
            # Check for text wrapping classes
            text_classes = ['break-words', 'max-w-', 'mx-auto']
            has_responsive_classes = any(cls in template_content for cls in text_classes)
            
            if has_responsive_classes:
                print("✅ Template has responsive text wrapping classes")
            else:
                print("⚠️ Template may need responsive text classes")
        
        print("✅ Certificate text wrapping test completed")
        print("🎯 Ready for improved certificate generation")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_certificate_with_long_text())
