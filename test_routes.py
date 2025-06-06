#!/usr/bin/env python3
"""
Simple test to check route accessibility
"""

import requests

def test_basic_routes():
    base_url = "http://localhost:8000"
    
    # Test basic routes
    routes_to_test = [
        "/",
        "/client/",
        "/client/login"
    ]
    
    for route in routes_to_test:
        try:
            response = requests.get(f"{base_url}{route}", timeout=5)
            print(f"{route}: Status {response.status_code}")
        except Exception as e:
            print(f"{route}: Error - {str(e)}")

if __name__ == "__main__":
    test_basic_routes()
