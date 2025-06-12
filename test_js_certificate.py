#!/usr/bin/env python3
"""
Test the JavaScript Certificate Generator Backend
Quick test to verify the API endpoints work correctly
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.js_certificate_generator import get_certificate_data_for_js, send_certificate_email_from_js


async def test_certificate_data_api():
    """Test the certificate data API"""
    print("🧪 Testing JavaScript Certificate Generator API")
    print("=" * 50)
    
    # Test with known working data
    event_id = "DIGITAL_LITERACY_WORKSHOP_2025"
    enrollment_no = "22BEIT30043"  # Shivansh Ghelani
    
    print(f"📋 Testing certificate data for:")
    print(f"   Event: {event_id}")
    print(f"   Student: {enrollment_no}")
    
    # Test certificate data retrieval
    success, message, data = await get_certificate_data_for_js(event_id, enrollment_no)
    
    if success:
        print(f"✅ Certificate data retrieved successfully!")
        print(f"   Message: {message}")
        print(f"   Student Name: {data['student_data']['full_name']}")
        print(f"   Event Name: {data['event_data']['event_name']}")
        print(f"   Template Length: {len(data['template_html'])} characters")
        
        if data.get('team_data'):
            print(f"   Team Name: {data['team_data']['team_name']}")
        else:
            print(f"   Registration Mode: Individual")
            
        return True
    else:
        print(f"❌ Certificate data retrieval failed:")
        print(f"   Error: {message}")
        return False


async def test_email_api():
    """Test the email API with dummy data"""
    print("\n📧 Testing email API with dummy PDF data...")
    
    # Test with minimal dummy data
    event_id = "DIGITAL_LITERACY_WORKSHOP_2025"
    enrollment_no = "22BEIT30043"  # Shivansh Ghelani
    
    # Create a small dummy PDF in base64 (just for testing the API)
    dummy_pdf_content = b"Dummy PDF content for testing"
    import base64
    pdf_base64 = base64.b64encode(dummy_pdf_content).decode()
    file_name = "test_certificate.pdf"
    
    success, message = await send_certificate_email_from_js(
        event_id, enrollment_no, pdf_base64, file_name
    )
    
    if success:
        print(f"✅ Email API test successful!")
        print(f"   Message: {message}")
        return True
    else:
        print(f"❌ Email API test failed:")
        print(f"   Error: {message}")
        return False


async def main():
    """Run all tests"""
    print("🎯 JavaScript Certificate Generator Backend Test")
    print("=" * 60)
    
    try:
        # Test certificate data API
        data_success = await test_certificate_data_api()
        
        # Test email API (only if data API works)
        if data_success:
            email_success = await test_email_api()
        else:
            email_success = False
            
        print("\n" + "=" * 60)
        print("📊 Test Results:")
        print(f"   Certificate Data API: {'✅ PASS' if data_success else '❌ FAIL'}")
        print(f"   Email API: {'✅ PASS' if email_success else '❌ FAIL'}")
        
        if data_success and email_success:
            print("\n🎉 All tests passed! JavaScript certificate generator backend is ready!")
        else:
            print("\n⚠️ Some tests failed. Check the errors above.")
            
    except Exception as e:
        print(f"\n💥 Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
