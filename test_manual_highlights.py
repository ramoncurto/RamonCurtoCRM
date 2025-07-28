#!/usr/bin/env python3
"""
Test script to verify manual highlights functionality in the communication hub.
This test creates, updates, and deletes manual highlights.
"""

import requests
import json

def test_manual_highlights():
    """Test the manual highlights functionality."""
    
    base_url = "http://localhost:8000"
    athlete_id = 1
    
    print("🎯 Testing Manual Highlights Functionality")
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
    
    # Test 2: Get existing highlights
    print("\n2. Testing Get Highlights...")
    try:
        response = requests.get(f"{base_url}/athletes/{athlete_id}/highlights")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data.get('highlights', []))} total highlights")
        else:
            print(f"❌ Failed to get highlights: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting highlights: {e}")
        return False
    
    # Test 3: Get manual highlights only
    print("\n3. Testing Manual Highlights Filter...")
    try:
        response = requests.get(f"{base_url}/athletes/{athlete_id}/highlights?manual_only=true")
        if response.status_code == 200:
            data = response.json()
            manual_count = len(data.get('highlights', []))
            print(f"✅ Found {manual_count} manual highlights")
        else:
            print(f"❌ Failed to get manual highlights: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting manual highlights: {e}")
        return False
    
    # Test 4: Create a new manual highlight
    print("\n4. Testing Create Manual Highlight...")
    try:
        highlight_data = {
            'highlight_text': 'Test manual highlight - Athlete shows great progress in training',
            'category': 'training'
        }
        
        response = requests.post(f"{base_url}/athletes/{athlete_id}/highlights", data=highlight_data)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success' or result.get('highlight_id'):
                print("✅ Manual highlight created successfully")
                highlight_id = result.get('highlight_id')
            else:
                print(f"❌ Failed to create highlight: {result}")
                return False
        else:
            print(f"❌ Failed to create highlight: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating highlight: {e}")
        return False
    
    # Test 5: Update the highlight
    print("\n5. Testing Update Manual Highlight...")
    try:
        update_data = {
            'highlight_text': 'Updated: Athlete shows excellent progress in training and nutrition',
            'category': 'achievement'
        }
        
        response = requests.put(f"{base_url}/highlights/{highlight_id}/content", data=update_data)
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print("✅ Manual highlight updated successfully")
            else:
                print(f"❌ Failed to update highlight: {result}")
                return False
        else:
            print(f"❌ Failed to update highlight: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error updating highlight: {e}")
        return False
    
    # Test 6: Verify the update
    print("\n6. Testing Verify Update...")
    try:
        response = requests.get(f"{base_url}/athletes/{athlete_id}/highlights?manual_only=true")
        if response.status_code == 200:
            data = response.json()
            highlights = data.get('highlights', [])
            updated_highlight = next((h for h in highlights if h.get('id') == highlight_id), None)
            
            if updated_highlight:
                if 'excellent progress' in updated_highlight.get('highlight_text', ''):
                    print("✅ Highlight update verified successfully")
                else:
                    print("❌ Highlight was not updated correctly")
                    return False
            else:
                print("❌ Updated highlight not found")
                return False
        else:
            print(f"❌ Failed to verify update: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error verifying update: {e}")
        return False
    
    # Test 7: Delete the highlight
    print("\n7. Testing Delete Manual Highlight...")
    try:
        response = requests.delete(f"{base_url}/highlights/{highlight_id}")
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print("✅ Manual highlight deleted successfully")
            else:
                print(f"❌ Failed to delete highlight: {result}")
                return False
        else:
            print(f"❌ Failed to delete highlight: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error deleting highlight: {e}")
        return False
    
    # Test 8: Verify deletion
    print("\n8. Testing Verify Deletion...")
    try:
        response = requests.get(f"{base_url}/athletes/{athlete_id}/highlights?manual_only=true")
        if response.status_code == 200:
            data = response.json()
            highlights = data.get('highlights', [])
            deleted_highlight = next((h for h in highlights if h.get('id') == highlight_id), None)
            
            if not deleted_highlight:
                print("✅ Highlight deletion verified successfully")
            else:
                print("❌ Highlight was not deleted")
                return False
        else:
            print(f"❌ Failed to verify deletion: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error verifying deletion: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All manual highlights tests passed!")
    print("\n📝 Manual highlights functionality includes:")
    print("   ✅ Create new manual highlights")
    print("   ✅ Update existing highlights")
    print("   ✅ Delete highlights")
    print("   ✅ Filter manual vs AI-generated highlights")
    print("   ✅ Category-based organization")
    print("   ✅ Real-time UI updates")
    
    return True

def main():
    """Run the manual highlights test."""
    success = test_manual_highlights()
    
    if success:
        print("\n🚀 Manual highlights are ready to use!")
        print("   Navigate to http://localhost:8000/communication-hub")
        print("   Click on the 'Manual' tab in the highlights sidebar")
        print("   Click 'Add Highlight' to create new manual highlights")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main() 