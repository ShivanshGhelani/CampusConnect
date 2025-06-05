#!/usr/bin/env python3
"""
Test Automation Setup Script
============================

This script validates that all components needed for the event form automation
are properly configured and available without actually running the browser automation.

Author: UCG Development Team
"""

import json
import os
import sys
from pathlib import Path
import requests

def test_data_file():
    """Test if the event data JSON file exists and is valid."""
    print("🧪 Testing event data file...")
    
    data_file = Path(__file__).parent.parent.parent / "data" / "sample_event_data.json"
    
    if not data_file.exists():
        print(f"❌ Event data file not found at: {data_file}")
        return False
    
    try:
        with open(data_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
            event_data = data.get('event_data', {})
            login_credentials = data.get('login_credentials', {})
            
        print(f"✅ Event data file loaded successfully")
        print(f"   📄 Event: {event_data.get('event_name', 'Unknown')}")
        print(f"   👤 Login User: {login_credentials.get('username', 'Unknown')}")
        print(f"   🔧 Event Type: {event_data.get('event_type', 'Unknown')}")
        print(f"   💰 Registration Type: {event_data.get('registration_type', 'Unknown')}")
        
        # Validate required fields
        required_fields = [
            'event_id', 'event_name', 'event_type', 'start_date', 'end_date',
            'registration_start_date', 'registration_end_date', 'mode', 'venue'
        ]
        
        missing_fields = [field for field in required_fields if not event_data.get(field)]
        if missing_fields:
            print(f"⚠️  Missing required fields: {missing_fields}")
            return False
        
        print("✅ All required fields present")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading data file: {e}")
        return False

def test_certificate_files():
    """Test if certificate template and asset files exist."""
    print("\n🧪 Testing certificate files...")
    
    data_file = Path(__file__).parent.parent.parent / "data" / "sample_event_data.json"
    
    try:
        with open(data_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
            event_data = data.get('event_data', {})
        
        # Check certificate template
        cert_template_path = event_data.get('certificate_template_path')
        if cert_template_path and os.path.exists(cert_template_path):
            print(f"✅ Certificate template found: {cert_template_path}")
            cert_template_ok = True
        else:
            print(f"❌ Certificate template not found: {cert_template_path}")
            cert_template_ok = False
        
        # Check asset files
        asset_files = event_data.get('asset_files', [])
        assets_ok = True
        
        if asset_files:
            print(f"🔍 Checking {len(asset_files)} asset file(s)...")
            for asset_file in asset_files:
                if os.path.exists(asset_file):
                    print(f"✅ Asset file found: {asset_file}")
                else:
                    print(f"❌ Asset file not found: {asset_file}")
                    assets_ok = False
        else:
            print("ℹ️  No asset files specified")
        
        return cert_template_ok and assets_ok
        
    except Exception as e:
        print(f"❌ Error checking certificate files: {e}")
        return False

def test_selenium_dependencies():
    """Test if Selenium and WebDriver Manager are available."""
    print("\n🧪 Testing Selenium dependencies...")
    
    try:
        import selenium
        print(f"✅ Selenium available (version: {selenium.__version__})")
        
        from webdriver_manager.chrome import ChromeDriverManager
        print("✅ WebDriver Manager available")
        
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait, Select
        print("✅ Selenium components imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking Selenium: {e}")
        return False

def test_server_connection():
    """Test if the web application server is accessible."""
    print("\n🧪 Testing server connection...")
    
    base_url = "http://localhost:8000"
    
    try:
        response = requests.get(base_url, timeout=5)
        print(f"✅ Server is accessible at {base_url}")
        print(f"   📊 Status code: {response.status_code}")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Server is not running at {base_url}")
        print("   💡 Start the server with: python main.py")
        return False
    except requests.exceptions.Timeout:
        print(f"⚠️  Server timeout at {base_url}")
        return False
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return False

def main():
    """Run all tests and provide summary."""
    print("🤖 UCG Event Form Automation - Setup Validation")
    print("=" * 60)
    
    test_results = {
        "data_file": test_data_file(),
        "certificate_files": test_certificate_files(),
        "selenium_deps": test_selenium_dependencies(),
        "server_connection": test_server_connection()
    }
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 All tests passed! Automation script is ready to run.")
        print("🚀 To run the automation: python scripts/automation/event_form_automation_optimized.py")
    else:
        print("⚠️  Some tests failed. Please fix the issues before running automation.")
        
        if not test_results["server_connection"]:
            print("\n💡 To start the server:")
            print("   cd s:\\Projects\\UCG_v2\\Admin")
            print("   python main.py")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
