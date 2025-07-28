#!/usr/bin/env python3
"""
Simple test to check template rendering
"""

import requests
import json

def test_simple_endpoint():
    """Test a simple endpoint that should work"""
    try:
        print("🧪 Testing simple endpoint...")
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Root endpoint works")
        else:
            print(f"   ❌ Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

def test_whatsapp_config():
    """Test the WhatsApp config endpoint"""
    try:
        print("\n🧪 Testing WhatsApp config...")
        response = requests.get("http://localhost:8000/test/whatsapp-config", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ WhatsApp config works")
            print(f"   📱 Twilio configured: {data.get('twilio', {}).get('configured', False)}")
        else:
            print(f"   ❌ WhatsApp config failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")

if __name__ == "__main__":
    test_simple_endpoint()
    test_whatsapp_config() 