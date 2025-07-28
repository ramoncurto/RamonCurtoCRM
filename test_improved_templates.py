#!/usr/bin/env python3
"""
Test script to check if improved templates work correctly
"""

import requests
import time

def test_improved_templates():
    """Test all improved template endpoints"""
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/dashboard",
        "/athletes", 
        "/history",
        "/communication-hub"
    ]
    
    print("🧪 Testing Improved Templates")
    print("=" * 40)
    
    for endpoint in endpoints:
        try:
            print(f"\n📄 Testing: {endpoint}")
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ Success: {response.status_code}")
                print(f"   📏 Content length: {len(response.text)} characters")
                
                # Check if it's using improved template
                if "improved_base.html" in response.text or "Elite CRM" in response.text:
                    print("   🎨 Using improved template")
                else:
                    print("   ⚠️  Not using improved template")
                    
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   📄 Response: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection failed - server not running")
            break
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
    
    print("\n🎯 Summary:")
    print("   If all endpoints return 200, the improved templates are working!")
    print("   If you see errors, check the server logs for template issues.")

if __name__ == "__main__":
    test_improved_templates() 