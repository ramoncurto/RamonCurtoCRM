#!/usr/bin/env python3
"""
Test script for Human-in-the-Loop highlights functionality
"""

import asyncio
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_hil_highlights():
    """Test the HIL highlights workflow"""
    print("🧪 Testing Human-in-the-Loop Highlights System")
    print("=" * 50)
    
    # 1. First, let's create a test message
    print("\n1. Creating test message...")
    message_data = {
        "athlete_id": 1,
        "content_text": "I've been feeling some pain in my left knee during training. Should I continue with the current program or modify it? Also, I'd like to schedule a session next week.",
        "source_channel": "manual",
        "generate_highlights": True
    }
    
    response = requests.post(f"{BASE_URL}/ingest/manual", json=message_data)
    print(f"Response: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Message created: {result}")
        message_id = result.get("result", {}).get("message_id")
    else:
        print(f"❌ Error creating message: {response.text}")
        return
    
    # 2. Generate highlights for the message
    print(f"\n2. Generating highlights for message {message_id}...")
    response = requests.post(f"{BASE_URL}/messages/{message_id}/highlights/generate")
    print(f"Response: {response.status_code}")
    if response.status_code == 200:
        highlights = response.json()
        print(f"✅ Generated highlights: {json.dumps(highlights, indent=2)}")
        
        # Get the highlight IDs for testing - we need to fetch them from the database
        # since the generation doesn't return IDs
        response = requests.get(f"{BASE_URL}/highlights/1?status=suggested&source=ai")
        if response.status_code == 200:
            highlights_data = response.json()
            highlight_ids = [h.get("id") for h in highlights_data.get("highlights", [])]
            print(f"✅ Found {len(highlight_ids)} highlight IDs: {highlight_ids}")
        else:
            print(f"❌ Error fetching highlights: {response.text}")
            return
    else:
        print(f"❌ Error generating highlights: {response.text}")
        return
    
    # 3. Test individual highlight update
    if highlight_ids:
        print(f"\n3. Testing individual highlight update...")
        highlight_id = highlight_ids[0]
        update_data = {
            "text": "Modified: Knee pain during training - needs assessment",
            "category": "injury",
            "status": "accepted",
            "reviewed_by": "coach_test"
        }
        
        response = requests.patch(f"{BASE_URL}/highlights/{highlight_id}", json=update_data)
        print(f"Response: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Highlight updated successfully")
        else:
            print(f"❌ Error updating highlight: {response.text}")
    
    # 4. Test bulk update (accept all)
    print(f"\n4. Testing bulk accept all...")
    bulk_data = {
        "highlight_ids": highlight_ids,
        "status": "accepted",
        "reviewed_by": "coach_test"
    }
    
    response = requests.post(f"{BASE_URL}/highlights/bulk", json=bulk_data)
    print(f"Response: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ Bulk update successful")
    else:
        print(f"❌ Error bulk updating: {response.text}")
    
    # 5. Test filtering highlights
    print(f"\n5. Testing highlight filtering...")
    response = requests.get(f"{BASE_URL}/highlights/1?status=accepted&source=ai")
    print(f"Response: {response.status_code}")
    if response.status_code == 200:
        highlights = response.json()
        print(f"✅ Filtered highlights: {json.dumps(highlights, indent=2)}")
    else:
        print(f"❌ Error filtering highlights: {response.text}")
    
    print("\n🎉 HIL Highlights test completed!")

if __name__ == "__main__":
    test_hil_highlights() 