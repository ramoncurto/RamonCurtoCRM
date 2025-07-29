#!/usr/bin/env python3
"""
Script to disable automatic GPT requests
"""

import os

def create_env_file():
    """Create or update .env file to disable automatic GPT"""
    
    env_content = """# Disable automatic GPT requests
AUTO_GPT_ENABLED=false

# OpenAI API Key (if you want to keep it for manual requests)
# OPENAI_API_KEY=your_openai_api_key_here
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file with AUTO_GPT_ENABLED=false")
        print("📝 Automatic GPT requests are now disabled")
        print("🔄 Restart your server to apply changes")
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")

def check_current_setting():
    """Check current AUTO_GPT_ENABLED setting"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        auto_gpt_enabled = os.getenv("AUTO_GPT_ENABLED", "true").lower() == "true"
        
        print(f"🔍 Current AUTO_GPT_ENABLED setting: {auto_gpt_enabled}")
        
        if auto_gpt_enabled:
            print("⚠️  Automatic GPT requests are currently ENABLED")
            print("💡 Run this script to disable them")
        else:
            print("✅ Automatic GPT requests are currently DISABLED")
            
    except Exception as e:
        print(f"❌ Error checking settings: {e}")

if __name__ == "__main__":
    print("🏆 Elite Athlete CRM - GPT Control")
    print("=" * 40)
    
    check_current_setting()
    print()
    
    response = input("Do you want to disable automatic GPT requests? (y/n): ")
    
    if response.lower() in ['y', 'yes']:
        create_env_file()
    else:
        print("❌ No changes made")