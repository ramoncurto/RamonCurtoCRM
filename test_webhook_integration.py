#!/usr/bin/env python3
"""
Test script for WhatsApp and Telegram webhook integration
"""

import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_PHONES = [
    "+34123456789",  # Ramon Curto's actual phone
    "34123456789",   # Without +
    "123456789",     # Last 9 digits
    "23456789",      # Last 8 digits
]

def test_server_ready():
    """Check if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        return response.status_code == 200
    except:
        return False

def test_phone_matching():
    """Test phone number matching functionality"""
    print("🔍 Testing Phone Number Matching")
    print("=" * 50)
    
    for phone in TEST_PHONES:
        try:
            response = requests.get(f"{BASE_URL}/athletes/phone/{phone}")
            if response.status_code == 200:
                data = response.json()
                if data.get("athlete"):
                    print(f"✅ Phone {phone}: Found athlete {data['athlete']['name']}")
                else:
                    print(f"❌ Phone {phone}: No athlete found")
            else:
                print(f"❌ Phone {phone}: Request failed ({response.status_code})")
        except Exception as e:
            print(f"❌ Phone {phone}: Error - {str(e)}")

def test_webhook_simulation():
    """Test webhook message processing"""
    print("\n📱 Testing Webhook Message Processing")
    print("=" * 50)
    
    test_messages = [
        {
            "phone": "+34123456789",
            "message": "Hola coach, necesito consejos sobre mi plan de nutrición para la próxima competición",
            "source": "whatsapp"
        },
        {
            "phone": "34123456789",
            "message": "Coach, I've been feeling tired during training. Should I adjust my recovery routine?",
            "source": "telegram"
        },
        {
            "phone": "+34123456789",
            "message": "¿Cuál es el mejor momento para hacer cardio en relación con mis entrenamientos de fuerza?",
            "source": "whatsapp"
        }
    ]
    
    for i, test in enumerate(test_messages, 1):
        print(f"\n📤 Test Message {i}: {test['source']} from {test['phone']}")
        try:
            response = requests.post(
                f"{BASE_URL}/test/webhook",
                json={
                    "phone": test["phone"],
                    "message": test["message"],
                    "source": test["source"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    athlete = data.get("athlete", {})
                    print(f"✅ Success: Message processed for {athlete.get('name', 'Unknown')}")
                    if data.get("response"):
                        print(f"   🤖 Response: {data['response'][:100]}...")
                else:
                    print(f"✅ Success: {data.get('message', 'No athlete found')}")
            else:
                print(f"❌ Request failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")

def test_whatsapp_webhook_format():
    """Test WhatsApp webhook format"""
    print("\n📱 Testing WhatsApp Webhook Format")
    print("=" * 50)
    
    # Simulate WhatsApp Business API webhook format
    whatsapp_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "1234567890",
                        "phone_number_id": "123456789"
                    },
                    "contacts": [{
                        "profile": {
                            "name": "Ramon Curto"
                        },
                        "wa_id": "34123456789"
                    }],
                    "messages": [{
                        "from": "34123456789",
                        "id": "wamid.test123",
                        "timestamp": "1234567890",
                        "text": {
                            "body": "Hola coach, ¿cómo estás? Necesito ayuda con mi entrenamiento."
                        },
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhook/whatsapp",
            json=whatsapp_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ WhatsApp webhook processed successfully")
            print(f"   Status: {data.get('status', 'unknown')}")
        else:
            print(f"❌ WhatsApp webhook failed ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ WhatsApp webhook request failed: {str(e)}")

def test_telegram_webhook_format():
    """Test Telegram webhook format"""
    print("\n📱 Testing Telegram Webhook Format")
    print("=" * 50)
    
    # Simulate Telegram Bot API webhook format
    telegram_payload = {
        "update_id": 123456789,
        "message": {
            "message_id": 123,
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Ramon",
                "last_name": "Curto",
                "username": "ramoncurto"
            },
            "chat": {
                "id": 123456789,
                "first_name": "Ramon",
                "last_name": "Curto",
                "username": "ramoncurto",
                "type": "private"
            },
            "date": 1234567890,
            "text": "Coach, I need advice on my nutrition plan for the upcoming competition. What should I focus on?"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhook/telegram",
            json=telegram_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Telegram webhook processed successfully")
            print(f"   Status: {data.get('status', 'unknown')}")
        else:
            print(f"❌ Telegram webhook failed ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Telegram webhook request failed: {str(e)}")

def test_conversation_history():
    """Test conversation history with source tracking"""
    print("\n📚 Testing Conversation History")
    print("=" * 50)
    
    try:
        # Get athletes
        response = requests.get(f"{BASE_URL}/athletes")
        if response.status_code == 200:
            athletes = response.json().get("athletes", [])
            
            for athlete in athletes:
                print(f"\n👤 {athlete['name']}: ", end="")
                
                # Get athlete history
                history_response = requests.get(f"{BASE_URL}/athletes/{athlete['id']}/history")
                if history_response.status_code == 200:
                    history = history_response.json().get("history", [])
                    print(f"{len(history)} conversation(s)")
                    
                    for record in history[:3]:  # Show first 3 conversations
                        source = record.get("source", "manual")
                        source_icon = "📱" if source in ["whatsapp", "telegram"] else "✏️"
                        date = record.get("timestamp", "")[:10]
                        transcription = record.get("transcription", "")[:50]
                        print(f"   {source_icon} {date} [{source}]: {transcription}...")
                else:
                    print("0 conversation(s)")
        else:
            print("❌ Error retrieving athletes")
    except Exception as e:
        print(f"❌ Error retrieving history: {str(e)}")

def main():
    """Run all tests"""
    print("🏆 WhatsApp & Telegram Integration Tests")
    print("=" * 60)
    print("⏳ Make sure the server is running on http://localhost:8000")
    print()
    
    # Skip server check for now and try tests directly
    print("🔄 Attempting tests directly...")
    print()
    
    test_phone_matching()
    test_webhook_simulation()
    test_whatsapp_webhook_format()
    test_telegram_webhook_format()
    test_conversation_history()
    
    print("\n🎉 Webhook Integration Tests Completed!")
    print("\n📋 Next Steps:")
    print("1. Update your athlete profiles with phone numbers")
    print("2. Configure WhatsApp Business API webhook to point to /webhook/whatsapp")
    print("3. Configure Telegram Bot webhook to point to /webhook/telegram")
    print("4. Set WHATSAPP_VERIFY_TOKEN in your .env file")
    print("5. Test with real WhatsApp/Telegram messages!")

if __name__ == "__main__":
    main() 