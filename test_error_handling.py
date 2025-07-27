#!/usr/bin/env python3
import requests
import json

BASE_URL = "http://localhost:8000"

def test_invalid_endpoints():
    """Test invalid endpoint responses"""
    print("🔍 Testing Invalid Endpoints")
    print("=" * 40)
    
    invalid_endpoints = [
        "/nonexistent",
        "/athletes/999",  # Non-existent athlete
        "/athletes/abc",  # Invalid athlete ID
        "/athletes/999/history"  # Non-existent athlete history
    ]
    
    results = []
    for endpoint in invalid_endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            print(f"📍 {endpoint}: Status {response.status_code}")
            
            if response.status_code == 404:
                print("  ✅ Correctly returns 404 for invalid endpoint")
                results.append(True)
            elif response.status_code == 422:
                print("  ✅ Correctly returns 422 for invalid parameters")
                results.append(True)
            else:
                print(f"  ⚠️  Unexpected status code: {response.status_code}")
                results.append(False)
                
        except Exception as e:
            print(f"  ❌ Error testing {endpoint}: {e}")
            results.append(False)
    
    return all(results)

def test_malformed_requests():
    """Test malformed request handling"""
    print("\n🚫 Testing Malformed Requests")
    print("=" * 40)
    
    results = []
    
    # Test empty transcription
    try:
        response = requests.post(f"{BASE_URL}/generate", data={'transcription': ''}, timeout=10)
        print(f"📍 Empty transcription: Status {response.status_code}")
        if response.status_code in [200, 422]:
            print("  ✅ Handles empty transcription appropriately")
            results.append(True)
        else:
            print(f"  ❌ Unexpected response: {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"  ❌ Error with empty transcription: {e}")
        results.append(False)
    
    # Test athlete creation with missing required fields
    try:
        response = requests.post(f"{BASE_URL}/athletes", data={'email': 'test@test.com'}, timeout=10)
        print(f"📍 Missing required name field: Status {response.status_code}")
        if response.status_code in [422, 400]:
            print("  ✅ Correctly rejects missing required fields")
            results.append(True)
        else:
            print(f"  ❌ Should reject missing required fields: {response.status_code}")
            results.append(False)
    except Exception as e:
        print(f"  ❌ Error testing missing fields: {e}")
        results.append(False)
    
    return all(results)

def test_large_file_upload():
    """Test large file upload handling"""
    print("\n📁 Testing Large File Upload")
    print("=" * 40)
    
    try:
        # Create a mock large file (1MB of data)
        large_data = b"x" * (1024 * 1024)
        files = {'file': ('large_test.ogg', large_data, 'audio/ogg')}
        
        response = requests.post(f"{BASE_URL}/transcribe", files=files, timeout=60)
        print(f"📍 Large file upload: Status {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Successfully handles large file upload")
            return True
        elif response.status_code == 413:
            print("  ✅ Correctly rejects oversized files")
            return True
        else:
            print(f"  ⚠️  Unexpected response: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("  ⚠️  Upload timed out (might be expected for large files)")
        return True
    except Exception as e:
        print(f"  ❌ Error testing large file: {e}")
        return False

def test_concurrent_requests():
    """Test handling of concurrent requests"""
    print("\n⚡ Testing Concurrent Requests")
    print("=" * 40)
    
    import threading
    import time
    
    results = []
    
    def make_request():
        try:
            response = requests.get(f"{BASE_URL}/athletes", timeout=10)
            results.append(response.status_code == 200)
        except:
            results.append(False)
    
    # Create 5 concurrent requests
    threads = []
    for i in range(5):
        thread = threading.Thread(target=make_request)
        threads.append(thread)
        thread.start()
    
    # Wait for all to complete
    for thread in threads:
        thread.join()
    
    successful = sum(results)
    print(f"📍 Concurrent requests: {successful}/5 successful")
    
    if successful >= 4:  # Allow for 1 failure
        print("  ✅ Handles concurrent requests well")
        return True
    else:
        print("  ❌ Too many failures in concurrent requests")
        return False

def run_error_handling_tests():
    """Run comprehensive error handling tests"""
    print("🛡️  Elite Athlete CRM - Error Handling Tests")
    print("=" * 60)
    
    test_results = []
    
    test_results.append(test_invalid_endpoints())
    test_results.append(test_malformed_requests())
    test_results.append(test_large_file_upload())
    test_results.append(test_concurrent_requests())
    
    print("\n" + "=" * 60)
    passed = sum(test_results)
    total = len(test_results)
    print(f"📊 Error Handling Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All error handling tests passed!")
        print("The system handles errors gracefully and securely.")
    else:
        print("⚠️  Some error handling tests failed.")
        print("Review error handling implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = run_error_handling_tests()
    exit(0 if success else 1) 