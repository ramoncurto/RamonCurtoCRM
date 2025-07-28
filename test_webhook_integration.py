import requests
import json
import time

# Test the webhook integration functionality

BASE_URL = "http://localhost:8000"

def test_phone_matching():
    """Test the phone number matching functionality."""
    print("🔍 Testing Phone Number Matching")
    print("=" * 50)
    
    # Test with different phone number formats
    test_phones = [
        "+34679795648",  # International format
        "34679795648",   # Without +
        "0679795648",    # With leading 0
        "679-795-648",   # With dashes
        "679 795 648",   # With spaces
    ]
    
    for phone in test_phones:
        try:
            response = requests.get(f"{BASE_URL}/athletes/phone/{phone}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Phone {phone}: Found athlete {data['athlete']['name']}")
            elif response.status_code == 404:
                print(f"❌ Phone {phone}: No athlete found")
            else:
                print(f"⚠️  Phone {phone}: Unexpected status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Phone {phone}: Error - {e}")
    
    print()


def test_webhook_simulation():
    """Test the webhook functionality with simulated messages."""
    print("📱 Testing Webhook Message Processing")
    print("=" * 50)
    
    # Test messages from different sources
    test_messages = [
        {
            "phone": "+34679795648",
            "message": "Hi coach! How should I prepare for my next competition?",
            "source": "whatsapp"
        },
        {
            "phone": "34679795648",
            "message": "I'm feeling some pain in my knee after training yesterday",
            "source": "telegram"
        },
        {
            "phone": "+34679795648",  # Non-existent athlete
            "message": "Hello, I'm a new athlete",
            "source": "test"
        }
    ]
    
    for i, test_data in enumerate(test_messages, 1):
        print(f"📤 Test Message {i}: {test_data['source']} from {test_data['phone']}")
        try:
            response = requests.post(f"{BASE_URL}/test/webhook", json=test_data)
            data = response.json()
            
            if response.status_code == 200:
                print(f"✅ Success: {data['message']}")
                if 'athlete' in data:
                    print(f"   👤 Athlete: {data['athlete']['name']}")
                if 'response' in data and data['response']:
                    print(f"   🤖 AI Response: {data['response'][:100]}...")
            else:
                print(f"❌ Error ({response.status_code}): {data.get('message', 'Unknown error')}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        
        print()


def test_whatsapp_webhook_format():
    """Test WhatsApp webhook with realistic payload format."""
    print("📱 Testing WhatsApp Webhook Format")
    print("=" * 50)
    
    # Simulate a Twilio WhatsApp webhook payload
    whatsapp_payload = {
        "messages": [
            {
                "from": "whatsapp:+34679795648",
                "id": "wamid.ABC123",
                "text": {
                    "body": "Coach, I completed my training session today. My times are improving!"
                },
                "timestamp": "1640995200",
                "type": "text"
            }
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/webhook/whatsapp", json=whatsapp_payload)
        data = response.json()
        
        if response.status_code == 200:
            print(f"✅ WhatsApp webhook processed successfully")
            print(f"   Status: {data.get('status')}")
            if 'athlete' in data:
                print(f"   👤 Athlete: {data['athlete']}")
            if 'response' in data:
                print(f"   🤖 Response: {data['response'][:100]}...")
        else:
            print(f"❌ WhatsApp webhook failed ({response.status_code}): {data}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ WhatsApp webhook request failed: {e}")
    
    print()


def test_telegram_webhook_format():
    """Test Telegram webhook with realistic payload format."""
    print("📱 Testing Telegram Webhook Format")
    print("=" * 50)
    
    # Simulate a Telegram Bot API webhook payload
    telegram_payload = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 987654321,
                "is_bot": False,
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe"
            },
            "chat": {
                "id": 987654321,
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe",
                "type": "private"
            },
            "date": 1640995200,
            "text": "I need advice on my nutrition plan for the upcoming season",
            "contact": {
                "phone_number": "+34123456789",
                "first_name": "John",
                "last_name": "Doe"
            }
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/webhook/telegram", json=telegram_payload)
        data = response.json()
        
        if response.status_code == 200:
            print(f"✅ Telegram webhook processed successfully")
            print(f"   Status: {data.get('status')}")
            if 'athlete' in data:
                print(f"   👤 Athlete: {data['athlete']}")
            if 'response' in data:
                print(f"   🤖 Response: {data['response'][:100]}...")
        else:
            print(f"❌ Telegram webhook failed ({response.status_code}): {data}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Telegram webhook request failed: {e}")
    
    print()


def test_conversation_history():
    """Check if conversations were saved correctly."""
    print("📚 Testing Conversation History")
    print("=" * 50)
    
    try:
        # Get all athletes
        response = requests.get(f"{BASE_URL}/athletes")
        athletes_data = response.json()
        
        for athlete in athletes_data.get('athletes', []):
            athlete_id = athlete['id']
            athlete_name = athlete['name']
            
            # Get history for this athlete
            history_response = requests.get(f"{BASE_URL}/athletes/{athlete_id}/history")
            history_data = history_response.json()
            
            conversations = history_data.get('history', [])
            print(f"👤 {athlete_name}: {len(conversations)} conversation(s)")
            
            for conv in conversations[-3:]:  # Show last 3 conversations
                source = conv.get('source', 'manual')
                timestamp = conv.get('timestamp', '')
                transcription = conv.get('transcription', '')[:50]
                
                print(f"   📝 {timestamp[:19]} [{source}]: {transcription}...")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error retrieving history: {e}")
    
    print()


def main():
    """Run all webhook integration tests."""
    print("🏆 WhatsApp & Telegram Integration Tests")
    print("=" * 60)
    print("⏳ Make sure the server is running on http://localhost:8000")
    print()
    
    # Wait for server to be ready
    for i in range(5):
        try:
            response = requests.get(f"{BASE_URL}/dashboard")
            if response.status_code == 200:
                break
        except:
            if i == 4:
                print("❌ Server not responding. Please start the server first.")
                return
            time.sleep(1)
    
    print("✅ Server is ready!")
    print()
    
    # Run all tests
    test_phone_matching()
    test_webhook_simulation()
    test_whatsapp_webhook_format()
    test_telegram_webhook_format()
    test_conversation_history()
    
    print("🎉 Webhook Integration Tests Completed!")
    print()
    print("📋 Next Steps:")
    print("1. Update your athlete profiles with phone numbers")
    print("2. Configure WhatsApp Business API webhook to point to /webhook/whatsapp")
    print("3. Configure Telegram Bot webhook to point to /webhook/telegram")
    print("4. Set WHATSAPP_VERIFY_TOKEN in your .env file")
    print("5. Test with real WhatsApp/Telegram messages!")


if __name__ == "__main__":
    main() 