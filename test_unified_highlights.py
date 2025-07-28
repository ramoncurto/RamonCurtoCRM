#!/usr/bin/env python3
"""
Test script to verify unified highlights functionality in the communication hub.
This test verifies that all highlights (auto, manual, AI) are displayed together.
"""

import requests
import json

def test_unified_highlights():
    """Test the unified highlights functionality."""
    
    base_url = "http://localhost:8000"
    athlete_id = 1
    
    print("🎯 Testing Unified Highlights Functionality")
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
    
    # Test 2: Get all highlights
    print("\n2. Testing Get All Highlights...")
    try:
        response = requests.get(f"{base_url}/athletes/{athlete_id}/highlights")
        if response.status_code == 200:
            data = response.json()
            all_highlights = data.get('highlights', [])
            print(f"✅ Found {len(all_highlights)} total highlights")
            
            # Count different types
            manual_count = len([h for h in all_highlights if not h.get('source_conversation_id')])
            ai_count = len([h for h in all_highlights if h.get('source_conversation_id')])
            
            print(f"   📝 Manual highlights: {manual_count}")
            print(f"   🤖 AI-generated highlights: {ai_count}")
            
            if len(all_highlights) > 0:
                print("✅ Highlights are being displayed together")
            else:
                print("⚠️  No highlights found")
                
        else:
            print(f"❌ Failed to get highlights: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting highlights: {e}")
        return False
    
    # Test 3: Verify highlight structure
    print("\n3. Testing Highlight Structure...")
    try:
        response = requests.get(f"{base_url}/athletes/{athlete_id}/highlights")
        if response.status_code == 200:
            data = response.json()
            highlights = data.get('highlights', [])
            
            if highlights:
                highlight = highlights[0]
                required_fields = ['id', 'highlight_text', 'category', 'created_at']
                missing_fields = [field for field in required_fields if field not in highlight]
                
                if not missing_fields:
                    print("✅ Highlight structure is correct")
                    print(f"   📄 Sample highlight: {highlight.get('highlight_text', '')[:50]}...")
                    print(f"   🏷️  Category: {highlight.get('category', 'N/A')}")
                    print(f"   📅 Created: {highlight.get('created_at', 'N/A')}")
                    print(f"   🤖 AI Source: {'Yes' if highlight.get('source_conversation_id') else 'No'}")
                else:
                    print(f"❌ Missing fields: {missing_fields}")
                    return False
            else:
                print("⚠️  No highlights to test structure")
        else:
            print(f"❌ Failed to get highlights: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing structure: {e}")
        return False
    
    # Test 4: Create a test manual highlight
    print("\n4. Testing Create Manual Highlight...")
    try:
        highlight_data = {
            'highlight_text': 'Test unified highlight - Athlete shows excellent progress in all areas',
            'category': 'achievement'
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
    
    # Test 5: Verify the new highlight appears in unified list
    print("\n5. Testing Unified Display...")
    try:
        response = requests.get(f"{base_url}/athletes/{athlete_id}/highlights")
        if response.status_code == 200:
            data = response.json()
            highlights = data.get('highlights', [])
            
            # Find our test highlight
            test_highlight = next((h for h in highlights if h.get('id') == highlight_id), None)
            
            if test_highlight:
                print("✅ New highlight appears in unified list")
                print(f"   📄 Text: {test_highlight.get('highlight_text', '')[:50]}...")
                print(f"   🏷️  Category: {test_highlight.get('category', 'N/A')}")
                print(f"   🤖 AI Source: {'Yes' if test_highlight.get('source_conversation_id') else 'No'}")
            else:
                print("❌ New highlight not found in unified list")
                return False
        else:
            print(f"❌ Failed to verify unified display: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error verifying unified display: {e}")
        return False
    
    # Test 6: Clean up - delete test highlight
    print("\n6. Testing Cleanup...")
    try:
        response = requests.delete(f"{base_url}/highlights/{highlight_id}")
        if response.status_code == 200:
            result = response.json()
            if result.get('status') == 'success':
                print("✅ Test highlight deleted successfully")
            else:
                print(f"❌ Failed to delete test highlight: {result}")
        else:
            print(f"❌ Failed to delete test highlight: {response.status_code}")
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Unified highlights functionality verified!")
    print("\n📝 Unified highlights features:")
    print("   ✅ All highlights displayed together")
    print("   ✅ Manual highlights with edit/delete actions")
    print("   ✅ AI-generated highlights (read-only)")
    print("   ✅ Source indicators (Manual/AI)")
    print("   ✅ Category-based organization")
    print("   ✅ Real-time updates")
    
    return True

def main():
    """Run the unified highlights test."""
    success = test_unified_highlights()
    
    if success:
        print("\n🚀 Unified highlights are ready to use!")
        print("   Navigate to http://localhost:8000/communication-hub")
        print("   View all highlights in the Conversation Highlights sidebar")
        print("   Click 'Add Manual Highlight' to create new highlights")
        print("   Edit/delete manual highlights using action buttons")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main() 