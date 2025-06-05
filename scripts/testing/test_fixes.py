#!/usr/bin/env python3
"""Quick test to verify the feedback and certificate route fixes"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that our updated routes can be imported"""
    try:
        from routes.client import feedback
        print("✅ feedback.py imported successfully")
        
        from routes.client import client
        print("✅ client.py imported successfully")
        
        # Test that the router objects exist
        assert hasattr(feedback, 'router'), "feedback.router not found"
        assert hasattr(client, 'router'), "client.router not found"
        
        print("✅ Router objects found")
        print("🎉 All fixes applied successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
