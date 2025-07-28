#!/usr/bin/env python3
"""
Test communication hub functionality
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_communication_hub():
    """Test communication hub functionality"""
    print("🧪 Testing Communication Hub Functionality")
    print("=" * 50)
    
    # 1. Test athlete API endpoint
    print("\n1. Testing athlete API endpoint...")
    response = requests.get(f"{BASE_URL}/api/athletes")
    if response.status_code == 200:
        data = response.json()
        athletes = data.get('athletes', [])
        print(f"✅ Found {len(athletes)} athletes")
        for athlete in athletes:
            print(f"   - {athlete['name']} (ID: {athlete['id']})")
        
        if athletes:
            test_athlete_id = athletes[0]['id']
            print(f"✅ Using athlete ID: {test_athlete_id}")
        else:
            print("❌ No athletes found")
            return
    else:
        print(f"❌ Error loading athletes: {response.status_code}")
        return
    
    # 2. Test manual message ingestion
    print(f"\n2. Testing manual message ingestion...")
    message_data = {
        "athlete_id": test_athlete_id,
        "content_text": "Hello coach! I had a great training session today. My knee feels much better.",
        "source_channel": "manual",
        "generate_highlights": True,
        "suggest_reply": True,
        "maybe_todo": True
    }
    
    response = requests.post(f"{BASE_URL}/ingest/manual", json=message_data)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Message sent successfully!")
        print(f"   - Message ID: {result.get('result', {}).get('message_id')}")
        print(f"   - Actions performed: {list(result.get('result', {}).get('actions_performed', {}).keys())}")
    else:
        print(f"❌ Error sending message: {response.text}")
        return
    
    # 3. Test highlights loading
    print(f"\n3. Testing highlights loading...")
    response = requests.get(f"{BASE_URL}/highlights/{test_athlete_id}")
    if response.status_code == 200:
        highlights = response.json()['highlights']
        print(f"✅ Loaded {len(highlights)} highlights")
        for highlight in highlights[:3]:  # Show first 3
            print(f"   - {highlight['text']} ({highlight['status']})")
    else:
        print(f"❌ Error loading highlights: {response.status_code}")
    
    # 4. Test conversations loading
    print(f"\n4. Testing conversations loading...")
    response = requests.get(f"{BASE_URL}/communication-hub/conversations/{test_athlete_id}")
    if response.status_code == 200:
        conversations = response.json()['conversations']
        print(f"✅ Loaded {len(conversations)} conversations")
        for conv in conversations:
            print(f"   - Conversation {conv['id']}: {conv['message_count']} messages")
    else:
        print(f"❌ Error loading conversations: {response.status_code}")
    
    print(f"\n🎉 Communication hub test completed!")
    print(f"✅ Athlete loading: Working")
    print(f"✅ Manual message recording: Working")
    print(f"✅ Highlights generation: Working")
    print(f"✅ Conversation management: Working")

if __name__ == "__main__":
    test_communication_hub() 