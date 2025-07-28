#!/usr/bin/env python3
"""
Test script for the complete workflow system
"""

import asyncio
import requests
import json
from datetime import datetime

def test_workflow_endpoints():
    """Test all workflow endpoints"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Complete Workflow System")
    print("=" * 50)
    
    # Test 1: Manual message ingestion
    print("\n📝 Test 1: Manual Message Ingestion")
    try:
        response = requests.post(f"{base_url}/ingest/manual", json={
            "athlete_id": 1,
            "content_text": "Hola coach, tengo una lesión en la rodilla y necesito reprogramar el entrenamiento de mañana.",
            "generate_highlights": True,
            "suggest_reply": True,
            "maybe_todo": True
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {data['status']}")
            if 'result' in data:
                print(f"   📊 Message ID: {data['result'].get('message_id')}")
                print(f"   🔍 Dedupe Hash: {data['result'].get('dedupe_hash')}")
                if 'actions_performed' in data['result']:
                    actions = data['result']['actions_performed']
                    if 'highlights' in actions:
                        print(f"   💡 Highlights generated: {len(actions['highlights'])}")
                    if 'suggested_reply' in actions:
                        print(f"   💬 Reply suggested: {len(actions['suggested_reply'])} chars")
                    if 'todo' in actions:
                        print(f"   ✅ Todo created: {actions['todo']}")
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   📄 Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    # Test 2: Get athlete conversations
    print("\n💬 Test 2: Get Athlete Conversations")
    try:
        response = requests.get(f"{base_url}/communication-hub/conversations/1")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {len(data['conversations'])} conversations found")
            for conv in data['conversations']:
                print(f"   📋 Conversation {conv['id']}: {conv['message_count']} messages")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    # Test 3: Get athlete highlights
    print("\n💡 Test 3: Get Athlete Highlights")
    try:
        response = requests.get(f"{base_url}/highlights/1")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {len(data['highlights'])} highlights found")
            for highlight in data['highlights']:
                print(f"   🏷️  {highlight['category']}: {highlight['text'][:50]}...")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    # Test 4: Get athlete todos
    print("\n✅ Test 4: Get Athlete Todos")
    try:
        response = requests.get(f"{base_url}/athletes/1/todos")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {len(data['todos'])} todos found")
            for todo in data['todos']:
                print(f"   📋 {todo['status']}: {todo['title']}")
        else:
            print(f"   ❌ Error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    # Test 5: Send message via WhatsApp
    print("\n📱 Test 5: Send Message via WhatsApp")
    try:
        response = requests.post(f"{base_url}/send/whatsapp", data={
            "athlete_id": 1,
            "message": "Hola! He revisado tu mensaje sobre la lesión. Te sugiero que descanses hoy y mañana evaluemos cómo te sientes. ¿Te parece bien?"
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {data['status']}")
            if 'result' in data:
                print(f"   📤 Result: {data['result']}")
        else:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   📄 Response: {response.text[:200]}...")
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
    
    print("\n🎯 Workflow Test Summary:")
    print("   If all tests show ✅ Success, the workflow is working!")
    print("   Check the server logs for any detailed error messages.")

def test_workflow_manual():
    """Test manual workflow actions"""
    base_url = "http://localhost:8000"
    
    print("\n🔧 Manual Workflow Actions Test")
    print("=" * 40)
    
    # First, create a message
    print("\n📝 Creating test message...")
    try:
        response = requests.post(f"{base_url}/ingest/manual", json={
            "athlete_id": 1,
            "content_text": "Necesito información sobre el horario de entrenamiento para la próxima semana.",
            "generate_highlights": False,
            "suggest_reply": False,
            "maybe_todo": False
        })
        
        if response.status_code == 200:
            data = response.json()
            message_id = data['result']['message_id']
            print(f"   ✅ Message created: {message_id}")
            
            # Test generating highlights for this message
            print(f"\n💡 Generating highlights for message {message_id}...")
            response = requests.post(f"{base_url}/messages/{message_id}/highlights/generate")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Highlights generated: {len(data['highlights'])}")
                for highlight in data['highlights']:
                    print(f"   🏷️  {highlight['category']}: {highlight['text']}")
            else:
                print(f"   ❌ Error: {response.status_code}")
            
            # Test suggesting reply for this message
            print(f"\n💬 Suggesting reply for message {message_id}...")
            response = requests.post(f"{base_url}/messages/{message_id}/reply/suggest")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Reply suggested: {data['suggested_reply'][:100]}...")
            else:
                print(f"   ❌ Error: {response.status_code}")
            
            # Test creating todo from this message
            print(f"\n✅ Creating todo from message {message_id}...")
            response = requests.post(f"{base_url}/messages/{message_id}/todo")
            
            if response.status_code == 200:
                data = response.json()
                if data['todo']:
                    print(f"   ✅ Todo created: {data['todo']['title']}")
                else:
                    print(f"   ℹ️  No actionable request detected")
            else:
                print(f"   ❌ Error: {response.status_code}")
                
        else:
            print(f"   ❌ Error creating message: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Workflow System Tests")
    print("Make sure the server is running on http://localhost:8000")
    print()
    
    test_workflow_endpoints()
    test_workflow_manual()
    
    print("\n🎉 Workflow testing completed!")
    print("Check the results above to verify the system is working correctly.") 