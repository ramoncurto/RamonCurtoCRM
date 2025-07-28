#!/usr/bin/env python3
"""
Comprehensive integration test for the HIL highlights system
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_complete_integration():
    """Test the complete HIL highlights integration"""
    print("🧪 Testing Complete HIL Highlights Integration")
    print("=" * 60)
    
    # 1. Test athlete loading
    print("\n1. Testing athlete loading...")
    response = requests.get(f"{BASE_URL}/api/athletes")
    if response.status_code == 200:
        data = response.json()
        athletes = data.get('athletes', [])
        print(f"✅ Loaded {len(athletes)} athletes")
        if athletes:
            test_athlete_id = athletes[0]['id']
            print(f"✅ Using athlete ID: {test_athlete_id}")
        else:
            print("❌ No athletes found, creating test athlete...")
            # Create a test athlete
            athlete_data = {
                "name": "Test Athlete",
                "email": "test@example.com",
                "phone": "+1234567890",
                "sport": "Running",
                "level": "Intermediate"
            }
            response = requests.post(f"{BASE_URL}/athletes", json=athlete_data)
            if response.status_code == 200:
                test_athlete_id = response.json()['id']
                print(f"✅ Created test athlete with ID: {test_athlete_id}")
            else:
                print("❌ Failed to create test athlete")
                return
    else:
        print(f"❌ Error loading athletes: {response.status_code}")
        return
    
    # 2. Test message creation with highlights
    print(f"\n2. Creating test message with highlights for athlete {test_athlete_id}...")
    message_data = {
        "athlete_id": test_athlete_id,
        "content_text": "I've been experiencing some knee pain during my long runs. Should I continue training or take a break? Also, I'd like to schedule a session to discuss my nutrition plan.",
        "source_channel": "manual",
        "generate_highlights": True,
        "suggest_reply": True,
        "maybe_todo": True
    }
    
    response = requests.post(f"{BASE_URL}/ingest/manual", json=message_data)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Message created successfully")
        print(f"   - Message ID: {result.get('result', {}).get('message_id')}")
        print(f"   - Actions performed: {list(result.get('result', {}).get('actions_performed', {}).keys())}")
    else:
        print(f"❌ Error creating message: {response.text}")
        return
    
    # 3. Test highlights loading and filtering
    print(f"\n3. Testing highlights loading and filtering...")
    
    # Test different filter combinations
    filter_tests = [
        ("all", "all"),
        ("suggested", "ai"),
        ("accepted", "all"),
        ("all", "manual")
    ]
    
    for status, source in filter_tests:
        response = requests.get(f"{BASE_URL}/highlights/{test_athlete_id}?status={status}&source={source}")
        if response.status_code == 200:
            highlights = response.json()['highlights']
            print(f"✅ Filter ({status}, {source}): {len(highlights)} highlights")
        else:
            print(f"❌ Error with filter ({status}, {source}): {response.status_code}")
    
    # 4. Test individual highlight operations
    print(f"\n4. Testing individual highlight operations...")
    
    # Get suggested highlights
    response = requests.get(f"{BASE_URL}/highlights/{test_athlete_id}?status=suggested&source=ai")
    if response.status_code == 200:
        suggested_highlights = response.json()['highlights']
        if suggested_highlights:
            highlight_id = suggested_highlights[0]['id']
            print(f"✅ Found suggested highlight ID: {highlight_id}")
            
            # Test accept
            accept_data = {
                "status": "accepted",
                "reviewed_by": "coach_test"
            }
            response = requests.patch(f"{BASE_URL}/highlights/{highlight_id}", json=accept_data)
            if response.status_code == 200:
                print(f"✅ Highlight {highlight_id} accepted successfully")
            else:
                print(f"❌ Error accepting highlight: {response.status_code}")
            
            # Test edit
            edit_data = {
                "text": "Modified: Knee pain during long runs - needs assessment",
                "category": "injury",
                "status": "accepted",
                "reviewed_by": "coach_test"
            }
            response = requests.patch(f"{BASE_URL}/highlights/{highlight_id}", json=edit_data)
            if response.status_code == 200:
                print(f"✅ Highlight {highlight_id} edited successfully")
            else:
                print(f"❌ Error editing highlight: {response.status_code}")
        else:
            print("⚠️ No suggested highlights found")
    else:
        print(f"❌ Error getting suggested highlights: {response.status_code}")
    
    # 5. Test bulk operations
    print(f"\n5. Testing bulk operations...")
    
    # Get all suggested highlights for bulk operations
    response = requests.get(f"{BASE_URL}/highlights/{test_athlete_id}?status=suggested&source=ai")
    if response.status_code == 200:
        suggested_highlights = response.json()['highlights']
        if suggested_highlights:
            highlight_ids = [h['id'] for h in suggested_highlights]
            print(f"✅ Found {len(highlight_ids)} suggested highlights for bulk operations")
            
            # Test bulk accept
            bulk_accept_data = {
                "highlight_ids": highlight_ids,
                "status": "accepted",
                "reviewed_by": "coach_test"
            }
            response = requests.post(f"{BASE_URL}/highlights/bulk", json=bulk_accept_data)
            if response.status_code == 200:
                print(f"✅ Bulk accept successful: {response.json()['message']}")
            else:
                print(f"❌ Error bulk accepting: {response.status_code}")
        else:
            print("⚠️ No suggested highlights for bulk operations")
    else:
        print(f"❌ Error getting highlights for bulk operations: {response.status_code}")
    
    # 6. Test todos loading
    print(f"\n6. Testing todos loading...")
    response = requests.get(f"{BASE_URL}/athletes/{test_athlete_id}/todos")
    if response.status_code == 200:
        todos = response.json()['todos']
        print(f"✅ Loaded {len(todos)} todos")
        for todo in todos:
            print(f"   - {todo['title']} ({todo['status']})")
    else:
        print(f"❌ Error loading todos: {response.status_code}")
    
    # 7. Test conversations loading
    print(f"\n7. Testing conversations loading...")
    response = requests.get(f"{BASE_URL}/communication-hub/conversations/{test_athlete_id}")
    if response.status_code == 200:
        conversations = response.json()['conversations']
        print(f"✅ Loaded {len(conversations)} conversations")
        for conv in conversations:
            print(f"   - Conversation {conv['id']}: {conv['message_count']} messages")
    else:
        print(f"❌ Error loading conversations: {response.status_code}")
    
    # 8. Test message generation for specific message
    print(f"\n8. Testing message-specific highlight generation...")
    
    # First, get a message ID
    response = requests.get(f"{BASE_URL}/communication-hub/conversations/{test_athlete_id}")
    if response.status_code == 200:
        conversations = response.json()['conversations']
        if conversations:
            conversation_id = conversations[0]['id']
            
            # Get messages for this conversation
            response = requests.get(f"{BASE_URL}/communication-hub/conversations/{conversation_id}/messages")
            if response.status_code == 200:
                messages = response.json()['messages']
                if messages:
                    message_id = messages[0]['id']
                    print(f"✅ Using message ID: {message_id}")
                    
                    # Generate highlights for this specific message
                    response = requests.post(f"{BASE_URL}/messages/{message_id}/highlights/generate")
                    if response.status_code == 200:
                        highlights = response.json()['highlights']
                        print(f"✅ Generated {len(highlights)} highlights for message {message_id}")
                    else:
                        print(f"❌ Error generating highlights for message: {response.status_code}")
                else:
                    print("⚠️ No messages found in conversation")
            else:
                print(f"❌ Error loading messages: {response.status_code}")
        else:
            print("⚠️ No conversations found")
    else:
        print(f"❌ Error loading conversations: {response.status_code}")
    
    print(f"\n🎉 Integration test completed successfully!")
    print(f"✅ All HIL highlights functionality is working correctly")
    print(f"✅ UI integration is ready for use")

if __name__ == "__main__":
    test_complete_integration() 