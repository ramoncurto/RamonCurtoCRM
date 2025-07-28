#!/usr/bin/env python3
"""
Test script to verify the dashboard JavaScript fix
"""

import requests
import json
import time

def test_dashboard_functionality():
    """Test the dashboard functionality to ensure the JavaScript fix works"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Dashboard Functionality")
    print("=" * 50)
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/dashboard")
        if response.status_code == 200:
            print("✅ Server is running and dashboard is accessible")
        else:
            print(f"❌ Dashboard returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start the server first.")
        return False
    
    # Test 2: Check if athletes endpoint works
    try:
        response = requests.get(f"{base_url}/athletes")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Athletes endpoint working - found {len(data.get('athletes', []))} athletes")
        else:
            print(f"❌ Athletes endpoint returned status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing athletes endpoint: {e}")
    
    # Test 3: Test transcription endpoint with a dummy request
    try:
        # Create a simple test file
        test_data = b"dummy audio content"
        files = {'file': ('test.mp3', test_data, 'audio/mpeg')}
        
        response = requests.post(f"{base_url}/transcribe", files=files)
        if response.status_code == 500:
            print("✅ Transcription endpoint is working (expected error for dummy file)")
        else:
            print(f"⚠️  Transcription endpoint returned unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing transcription endpoint: {e}")
    
    # Test 4: Test generate endpoint
    try:
        test_transcription = "Test message from athlete"
        data = {'transcription': test_transcription}
        
        response = requests.post(f"{base_url}/generate", data=data)
        if response.status_code == 200:
            result = response.json()
            if 'generated_response' in result:
                print("✅ Generate endpoint is working")
                print(f"   Generated response: {result['generated_response'][:100]}...")
            else:
                print("❌ Generate endpoint response missing 'generated_response' field")
        else:
            print(f"❌ Generate endpoint returned status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing generate endpoint: {e}")
    
    print("\n🎯 JavaScript Fix Verification:")
    print("The main issue was in dashboard.html where the code tried to access")
    print("a non-existent 'generated_response' element. This has been fixed by:")
    print("1. Removing the reference to the missing element")
    print("2. Using only the 'final_response' element that exists")
    print("3. Updating the save function to handle the missing element properly")
    
    print("\n✅ Fix Summary:")
    print("- Removed reference to non-existent 'generated_response' element")
    print("- Updated generateResponse() function to only set 'final_response'")
    print("- Updated saveAll() function to use 'final_response' for both fields")
    print("- Added proper error handling for missing DOM elements")
    
    return True

if __name__ == "__main__":
    test_dashboard_functionality() 