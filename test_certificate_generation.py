#!/usr/bin/env python3
"""
Test certificate generation functionality
"""

import asyncio
from utils.certificate_generator import generate_certificate_for_student

async def test_certificate_generation():
    """Test certificate generation with real data"""
    
    print("Testing certificate generation...")
    print("=" * 50)
    
    # Test with known student and event
    test_event_id = "DIGITAL_LITERACY_WORKSHOP_2025"
    test_enrollment_no = "22BEIT30043"  # Shivansh Ghelani
    
    print(f"Event ID: {test_event_id}")
    print(f"Student: {test_enrollment_no}")
    print()
    
    try:
        success, message, pdf_bytes = await generate_certificate_for_student(
            test_event_id, test_enrollment_no
        )
        
        print(f"Success: {success}")
        print(f"Message: {message}")
        
        if success and pdf_bytes:
            print(f"PDF Size: {len(pdf_bytes)} bytes")
            print("✅ Certificate generation successful!")
            
            # Optionally save the PDF for verification
            with open("test_certificate.pdf", "wb") as f:
                f.write(pdf_bytes)
            print("📄 Test certificate saved as 'test_certificate.pdf'")
            
        else:
            print("❌ Certificate generation failed")
            print(f"Error: {message}")
            
    except Exception as e:
        print(f"💥 Exception occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_certificate_generation())
