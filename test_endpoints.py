#!/usr/bin/env python3
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(name, url, expected_status=200, check_content=None):
    """Test a single endpoint"""
    try:
        print(f"🔗 Testing {name}: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code == expected_status:
            print(f"  ✅ Status: {response.status_code}")
            
            if check_content and check_content in response.text:
                print(f"  ✅ Content check passed: Found '{check_content}'")
            elif check_content:
                print(f"  ❌ Content check failed: '{check_content}' not found")
                return False
            
            return True
        else:
            print(f"  ❌ Status: {response.status_code} (expected {expected_status})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed: {e}")
        return False

def test_json_endpoint(name, url, expected_keys=None):
    """Test a JSON API endpoint"""
    try:
        print(f"🔗 Testing {name}: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"  ✅ Status: {response.status_code}")
            
            try:
                data = response.json()
                print(f"  ✅ Valid JSON response")
                
                if expected_keys:
                    for key in expected_keys:
                        if key in data:
                            print(f"  ✅ Found key: {key}")
                        else:
                            print(f"  ❌ Missing key: {key}")
                            return False
                
                print(f"  📊 Response preview: {str(data)[:100]}...")
                return True
                
            except json.JSONDecodeError:
                print(f"  ❌ Invalid JSON response")
                return False
        else:
            print(f"  ❌ Status: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed: {e}")
        return False

def test_post_endpoint(name, url, data):
    """Test a POST endpoint"""
    try:
        print(f"🔗 Testing {name}: {url}")
        response = requests.post(url, data=data, timeout=10)
        
        print(f"  📤 Request data: {data}")
        print(f"  📥 Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                print(f"  ✅ Response: {result}")
                return True
            except:
                print(f"  ✅ Response: {response.text[:100]}...")
                return True
        else:
            print(f"  ❌ Failed with status: {response.status_code}")
            print(f"  📝 Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed: {e}")
        return False

def run_comprehensive_test():
    """Run comprehensive endpoint testing"""
    print("🏆 Elite Athlete CRM - Comprehensive Workflow Test")
    print("=" * 60)
    
    # Wait for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(3)
    
    results = []
    
    # Test basic pages
    print("\n📱 Testing Web Pages:")
    results.append(test_endpoint("Dashboard", f"{BASE_URL}/dashboard", check_content="Elite Athlete CRM"))
    results.append(test_endpoint("Athletes Management", f"{BASE_URL}/athletes/manage", check_content="Athletes Management"))
    results.append(test_endpoint("History Page", f"{BASE_URL}/history", check_content="History"))
    
    # Test API endpoints
    print("\n🔌 Testing API Endpoints:")
    results.append(test_json_endpoint("Get Athletes", f"{BASE_URL}/athletes", ["athletes"]))
    results.append(test_json_endpoint("Get Records", f"{BASE_URL}/records"))
    
    # Test specific athlete endpoints
    print("\n👤 Testing Athlete-Specific Endpoints:")
    results.append(test_json_endpoint("Athlete 1 History", f"{BASE_URL}/athletes/1/history", ["history"]))
    results.append(test_json_endpoint("Athlete 1 Details", f"{BASE_URL}/athletes/1"))
    
    # Test POST endpoints (athlete creation)
    print("\n➕ Testing Create Operations:")
    test_athlete_data = {
        "name": "Test Athlete",
        "email": "test@example.com",
        "sport": "Testing",
        "level": "Beginner"
    }
    results.append(test_post_endpoint("Create Athlete", f"{BASE_URL}/athletes", test_athlete_data))
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All workflows are working correctly!")
    else:
        print("⚠️  Some workflows need attention.")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1) 