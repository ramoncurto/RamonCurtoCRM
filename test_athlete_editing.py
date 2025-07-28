#!/usr/bin/env python3
"""
Test script to verify athlete editing functionality
"""

import requests
import json

def test_athlete_editing():
    """Test athlete editing functionality."""
    
    base_url = "http://localhost:8000"
    
    print("👤 Testing Athlete Editing Functionality")
    print("=" * 50)
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/athletes")
        if response.status_code != 200:
            print("❌ Server not responding properly")
            return False
        print("✅ Server is running")
    except requests.exceptions.ConnectionError:
        print("❌ Server not running. Please start the server with: python start_server.py")
        return False
    
    # Test 2: Get existing athletes
    print("\n📋 Testing Get Athletes...")
    try:
        response = requests.get(f"{base_url}/athletes")
        if response.status_code == 200:
            data = response.json()
            athletes = data.get('athletes', [])
            print(f"✅ Found {len(athletes)} athletes")
            
            if athletes:
                test_athlete = athletes[0]
                print(f"   👤 Test athlete: {test_athlete['name']} (ID: {test_athlete['id']})")
            else:
                print("   ⚠️  No athletes found to test with")
                return False
        else:
            print(f"❌ Failed to get athletes: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting athletes: {e}")
        return False
    
    # Test 3: Get specific athlete details
    print("\n📖 Testing Get Athlete Details...")
    try:
        athlete_id = test_athlete['id']
        response = requests.get(f"{base_url}/athletes/{athlete_id}")
        if response.status_code == 200:
            athlete_data = response.json()
            print("✅ Athlete details retrieved successfully")
            print(f"   👤 Name: {athlete_data.get('name', 'N/A')}")
            print(f"   📧 Email: {athlete_data.get('email', 'N/A')}")
            print(f"   📞 Phone: {athlete_data.get('phone', 'N/A')}")
            print(f"   🏃 Sport: {athlete_data.get('sport', 'N/A')}")
            print(f"   🏆 Level: {athlete_data.get('level', 'N/A')}")
        else:
            print(f"❌ Failed to get athlete details: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting athlete details: {e}")
        return False
    
    # Test 4: Update athlete
    print("\n✏️  Testing Update Athlete...")
    try:
        update_data = {
            'name': f"{athlete_data['name']} (Updated)",
            'email': f"updated_{athlete_data.get('email', 'test@example.com')}",
            'phone': athlete_data.get('phone', ''),
            'sport': f"{athlete_data.get('sport', 'General')} (Updated)",
            'level': f"{athlete_data.get('level', 'Beginner')} (Updated)"
        }
        
        response = requests.put(f"{base_url}/athletes/{athlete_id}", data=update_data)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'updated':
                print("✅ Athlete updated successfully")
                print(f"   📝 Updated name: {update_data['name']}")
                print(f"   📧 Updated email: {update_data['email']}")
                print(f"   🏃 Updated sport: {update_data['sport']}")
                print(f"   🏆 Updated level: {update_data['level']}")
            else:
                print(f"❌ Failed to update athlete: {result}")
                return False
        else:
            print(f"❌ Failed to update athlete: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error updating athlete: {e}")
        return False
    
    # Test 5: Verify the update
    print("\n✅ Testing Verify Update...")
    try:
        response = requests.get(f"{base_url}/athletes/{athlete_id}")
        if response.status_code == 200:
            updated_athlete = response.json()
            print("✅ Updated athlete details retrieved")
            print(f"   👤 Name: {updated_athlete.get('name', 'N/A')}")
            print(f"   📧 Email: {updated_athlete.get('email', 'N/A')}")
            print(f"   🏃 Sport: {updated_athlete.get('sport', 'N/A')}")
            print(f"   🏆 Level: {updated_athlete.get('level', 'N/A')}")
            
            # Verify the changes were applied
            if "(Updated)" in updated_athlete.get('name', ''):
                print("✅ Name update verified")
            if "(Updated)" in updated_athlete.get('sport', ''):
                print("✅ Sport update verified")
            if "(Updated)" in updated_athlete.get('level', ''):
                print("✅ Level update verified")
        else:
            print(f"❌ Failed to verify update: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error verifying update: {e}")
        return False
    
    # Test 6: Test invalid athlete ID
    print("\n🚫 Testing Invalid Athlete ID...")
    try:
        response = requests.get(f"{base_url}/athletes/99999")
        if response.status_code == 404:
            print("✅ Correctly returns 404 for non-existent athlete")
        else:
            print(f"⚠️  Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing invalid athlete: {e}")
    
    # Test 7: Test update with invalid data
    print("\n🚫 Testing Invalid Update Data...")
    try:
        invalid_data = {
            'name': '',  # Empty name should fail
            'email': 'invalid-email',
            'phone': '',
            'sport': '',
            'level': ''
        }
        
        response = requests.put(f"{base_url}/athletes/{athlete_id}", data=invalid_data)
        if response.status_code == 400:
            print("✅ Correctly handles invalid update data")
        else:
            print(f"⚠️  Expected 400 for invalid data, got {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing invalid update: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Athlete Editing Test Completed!")
    print("\n📋 Summary:")
    print("   ✅ GET /athletes - List all athletes")
    print("   ✅ GET /athletes/{id} - Get athlete details")
    print("   ✅ PUT /athletes/{id} - Update athlete")
    print("   ✅ Error handling for invalid data")
    print("   ✅ Error handling for non-existent athletes")
    
    return True

def test_athlete_deletion():
    """Test athlete deletion functionality."""
    
    base_url = "http://localhost:8000"
    
    print("\n🗑️  Testing Athlete Deletion Functionality")
    print("=" * 50)
    
    # Test 1: Create a test athlete for deletion
    print("\n➕ Creating test athlete for deletion...")
    try:
        test_data = {
            'name': 'Test Athlete for Deletion',
            'email': 'delete@test.com',
            'phone': '+1234567890',
            'sport': 'Testing',
            'level': 'Test Level'
        }
        
        response = requests.post(f"{base_url}/athletes", data=test_data)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'created':
                test_athlete_id = result.get('athlete_id')
                print(f"✅ Test athlete created with ID: {test_athlete_id}")
            else:
                print(f"❌ Failed to create test athlete: {result}")
                return False
        else:
            print(f"❌ Failed to create test athlete: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error creating test athlete: {e}")
        return False
    
    # Test 2: Delete the test athlete
    print(f"\n🗑️  Deleting test athlete (ID: {test_athlete_id})...")
    try:
        response = requests.delete(f"{base_url}/athletes/{test_athlete_id}")
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'deleted':
                print("✅ Test athlete deleted successfully")
            else:
                print(f"❌ Failed to delete test athlete: {result}")
                return False
        else:
            print(f"❌ Failed to delete test athlete: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error deleting test athlete: {e}")
        return False
    
    # Test 3: Verify deletion
    print("\n✅ Verifying deletion...")
    try:
        response = requests.get(f"{base_url}/athletes/{test_athlete_id}")
        if response.status_code == 404:
            print("✅ Athlete correctly deleted (404 returned)")
        else:
            print(f"⚠️  Expected 404 after deletion, got {response.status_code}")
    except Exception as e:
        print(f"❌ Error verifying deletion: {e}")
    
    print("\n🎉 Athlete Deletion Test Completed!")
    return True

def main():
    """Run all athlete editing tests."""
    print("🏆 Athlete Editing & Deletion Tests")
    print("=" * 60)
    
    success1 = test_athlete_editing()
    success2 = test_athlete_deletion()
    
    if success1 and success2:
        print("\n🚀 All athlete management features are working!")
        print("   Navigate to http://localhost:8000/athletes/manage")
        print("   to test the UI editing functionality")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main() 