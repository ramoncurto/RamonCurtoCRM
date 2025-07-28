#!/usr/bin/env python3
"""
Twilio WhatsApp Sandbox Fix Script
Helps resolve the "Channel Sandbox can only send messages to phone numbers that have joined the Sandbox" error
"""

import os
import requests
import json

def check_twilio_config():
    """Check current Twilio configuration"""
    print("🔍 Checking Twilio WhatsApp Configuration")
    print("=" * 50)
    
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
    
    if account_sid and auth_token and whatsapp_number:
        print("✅ Twilio credentials found:")
        print(f"   Account SID: {account_sid[:10]}...")
        print(f"   Auth Token: {auth_token[:10]}...")
        print(f"   WhatsApp Number: {whatsapp_number}")
        return True
    else:
        print("❌ Twilio credentials missing:")
        print(f"   Account SID: {'✅' if account_sid else '❌'}")
        print(f"   Auth Token: {'✅' if auth_token else '❌'}")
        print(f"   WhatsApp Number: {'✅' if whatsapp_number else '❌'}")
        return False

def test_twilio_sandbox():
    """Test Twilio sandbox with different phone numbers"""
    print("\n🧪 Testing Twilio WhatsApp Sandbox")
    print("=" * 50)
    
    # Test phone numbers
    test_numbers = [
        "+34 679795648",  # Your athlete's number
        "+14155238886",   # Twilio's test number
        "+1234567890",    # Generic test number
    ]
    
    for phone in test_numbers:
        print(f"\n📱 Testing with: {phone}")
        
        try:
            response = requests.post(
                "http://localhost:8000/communication-hub/send-message",
                data={
                    "athlete_id": "1",  # Assuming athlete ID 1
                    "message": "Test message from Twilio sandbox fix",
                    "platform": "whatsapp"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   Status: {result.get('status', 'unknown')}")
                print(f"   Message: {result.get('message', 'No message')}")
                
                if result.get('status') == 'sent':
                    print("   ✅ Message sent successfully!")
                elif result.get('status') == 'error':
                    print(f"   ❌ Error: {result.get('message', 'Unknown error')}")
                else:
                    print(f"   ⚠️  Status: {result.get('status')}")
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {str(e)}")

def provide_sandbox_fix_instructions():
    """Provide step-by-step instructions to fix the sandbox issue"""
    print("\n🔧 Twilio WhatsApp Sandbox Fix Instructions")
    print("=" * 60)
    
    print("\n📋 **Step 1: Add Phone Number to Twilio Sandbox**")
    print("1. Go to: https://console.twilio.com/")
    print("2. Navigate to: Messaging → Try it out → Send a WhatsApp message")
    print("3. Add the athlete's phone number: +34 679795648")
    print("4. Send the join code to that number")
    print("5. The number will receive a WhatsApp message with a join code")
    print("6. Reply with the join code to activate the number")
    
    print("\n📋 **Step 2: Alternative - Use Twilio's Test Numbers**")
    print("For immediate testing, you can use these pre-approved numbers:")
    print("   • +14155238886 (Twilio's own test number)")
    print("   • Any number you've already added to your sandbox")
    
    print("\n📋 **Step 3: Test After Adding Number**")
    print("1. Add the phone number to your Twilio sandbox")
    print("2. Wait for the number to receive and reply with the join code")
    print("3. Test sending a message from your CRM")
    print("4. Check if the message is delivered successfully")
    
    print("\n📋 **Step 4: Production Setup (Optional)**")
    print("To exit sandbox mode and send to any number:")
    print("1. Go to: https://www.twilio.com/console/sms/whatsapp/sandbox")
    print("2. Click 'Request Production Access'")
    print("3. Fill out the business verification form")
    print("4. Wait for approval (usually 1-3 days)")
    print("5. Once approved, you can send to any verified number")

def check_server_status():
    """Check if the server is running"""
    print("🔍 Checking Server Status")
    print("=" * 30)
    
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running on http://localhost:8000")
            return True
        else:
            print(f"⚠️  Server responded with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not accessible: {str(e)}")
        print("💡 Make sure to run: python start_server.py")
        return False

def main():
    """Main function"""
    print("🏆 Twilio WhatsApp Sandbox Fix Tool")
    print("=" * 50)
    
    # Check server status
    if not check_server_status():
        print("\n❌ Please start the server first:")
        print("   python start_server.py")
        return
    
    # Check Twilio configuration
    if not check_twilio_config():
        print("\n❌ Please configure Twilio credentials first:")
        print("   Set environment variables or create .env file")
        return
    
    # Test current sandbox
    test_twilio_sandbox()
    
    # Provide fix instructions
    provide_sandbox_fix_instructions()
    
    print("\n🎯 **Quick Action Items:**")
    print("1. Add +34 679795648 to your Twilio WhatsApp sandbox")
    print("2. Wait for the join code and reply with it")
    print("3. Test sending a message from your CRM")
    print("4. If successful, add other athlete phone numbers")

if __name__ == "__main__":
    main() 