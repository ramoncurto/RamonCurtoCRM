#!/usr/bin/env python3
"""
Test script to verify the transcription service with OpenAI Whisper API.
"""

import asyncio
import os
from transcription_service import transcription_service

async def test_transcription():
    """Test the transcription service with a sample audio file."""
    
    # Check if OpenAI API key is configured
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key: export OPENAI_API_KEY='your-key-here'")
        return
    
    print("✅ OpenAI API key found")
    
    # Test transcription service initialization
    if not transcription_service.client:
        print("❌ Failed to initialize OpenAI client")
        return
    
    print("✅ OpenAI client initialized")
    
    # Look for test audio files in temp_audio_files directory
    test_dir = "temp_audio_files"
    if not os.path.exists(test_dir):
        print(f"❌ Test directory {test_dir} not found")
        return
    
    # Find audio files including .opus (WhatsApp format)
    audio_files = [f for f in os.listdir(test_dir) if f.endswith(('.mp3', '.wav', '.ogg', '.m4a', '.opus'))]
    
    if not audio_files:
        print("❌ No audio files found for testing")
        return
    
    print(f"✅ Found {len(audio_files)} audio files for testing")
    
    # Test with the first audio file
    test_file = os.path.join(test_dir, audio_files[0])
    print(f"🎵 Testing transcription with: {test_file}")
    
    # Check if it's a .opus file (WhatsApp format)
    if test_file.endswith('.opus'):
        print("📱 Detected WhatsApp .opus file format")
    
    try:
        transcription = await transcription_service.transcribe_audio(test_file)
        
        if transcription:
            print("✅ Transcription successful!")
            print(f"📝 Transcription: {transcription}")
        else:
            print("❌ Transcription returned None")
            
    except Exception as e:
        print(f"❌ Error during transcription: {e}")

if __name__ == "__main__":
    asyncio.run(test_transcription())
