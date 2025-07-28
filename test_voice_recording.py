#!/usr/bin/env python3
"""
Test script to verify voice recording functionality in the communication hub.
This test simulates the voice recording workflow and tests the /transcribe endpoint.
"""

import asyncio
import os
import requests
from pathlib import Path

def test_transcribe_endpoint():
    """Test the /transcribe endpoint with a sample audio file."""
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/athletes")
        if response.status_code != 200:
            print("❌ Server not responding properly")
            return False
        print("✅ Server is running")
    except requests.exceptions.ConnectionError:
        print("❌ Server not running. Please start the server with: python start_server.py")
        return False
    
    # Look for test audio files
    test_dir = "temp_audio_files"
    if not os.path.exists(test_dir):
        print(f"❌ Test directory {test_dir} not found")
        return False
    
    # Find audio files
    audio_files = [f for f in os.listdir(test_dir) if f.endswith(('.mp3', '.wav', '.ogg', '.m4a', '.opus'))]
    
    if not audio_files:
        print("❌ No audio files found for testing")
        return False
    
    print(f"✅ Found {len(audio_files)} audio files for testing")
    
    # Test with the first audio file
    test_file = os.path.join(test_dir, audio_files[0])
    print(f"🎵 Testing transcription with: {test_file}")
    
    try:
        # Test the /transcribe endpoint
        with open(test_file, 'rb') as audio_file:
            files = {'file': (audio_files[0], audio_file, 'audio/wav')}
            response = requests.post("http://localhost:8000/transcribe", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Transcription endpoint working!")
            print(f"📝 Transcription: {result.get('transcription', 'No transcription')}")
            print(f"📁 Filename: {result.get('filename', 'No filename')}")
            return True
        else:
            print(f"❌ Transcription endpoint failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during transcription test: {e}")
        return False

def test_communication_hub_access():
    """Test access to the communication hub page."""
    
    try:
        response = requests.get("http://localhost:8000/communication-hub")
        if response.status_code == 200:
            print("✅ Communication hub accessible")
            return True
        else:
            print(f"❌ Communication hub not accessible: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to communication hub")
        return False

def test_athletes_endpoint():
    """Test the /athletes endpoint that the communication hub depends on."""
    
    try:
        response = requests.get("http://localhost:8000/athletes")
        if response.status_code == 200:
            athletes = response.json()
            print(f"✅ Athletes endpoint working - found {len(athletes.get('athletes', []))} athletes")
            return True
        else:
            print(f"❌ Athletes endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing athletes endpoint: {e}")
        return False

def main():
    """Run all voice recording tests."""
    
    print("🎤 Testing Voice Recording Functionality")
    print("=" * 50)
    
    # Test 1: Communication hub accessibility
    print("\n1. Testing Communication Hub Access...")
    hub_ok = test_communication_hub_access()
    
    # Test 2: Athletes endpoint
    print("\n2. Testing Athletes Endpoint...")
    athletes_ok = test_athletes_endpoint()
    
    # Test 3: Transcription endpoint
    print("\n3. Testing Transcription Endpoint...")
    transcribe_ok = test_transcribe_endpoint()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Communication Hub: {'✅ PASS' if hub_ok else '❌ FAIL'}")
    print(f"   Athletes Endpoint: {'✅ PASS' if athletes_ok else '❌ FAIL'}")
    print(f"   Transcription: {'✅ PASS' if transcribe_ok else '❌ FAIL'}")
    
    if all([hub_ok, athletes_ok, transcribe_ok]):
        print("\n🎉 All tests passed! Voice recording should work in the communication hub.")
        print("\n📝 To test voice recording:")
        print("   1. Open http://localhost:8000/communication-hub in your browser")
        print("   2. Click the microphone button to start recording")
        print("   3. Speak into your microphone")
        print("   4. Click stop to transcribe your voice message")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main() 