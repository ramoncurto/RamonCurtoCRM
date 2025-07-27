#!/usr/bin/env python3
import requests
import json
import os
import io

BASE_URL = "http://localhost:8000"

def create_test_audio_file():
    """Create a simple test audio file content (mock)"""
    # Create a mock audio file content for testing
    test_content = b"MOCK_AUDIO_FILE_CONTENT_FOR_TESTING"
    return test_content

def test_audio_upload():
    """Test audio file upload and transcription"""
    print("🎤 Testing Audio Upload Workflow")
    print("=" * 50)
    
    # Create test audio data
    audio_content = create_test_audio_file()
    files = {
        'file': ('test_audio.ogg', io.BytesIO(audio_content), 'audio/ogg')
    }
    
    try:
        print("📤 Uploading test audio file...")
        response = requests.post(f"{BASE_URL}/transcribe", files=files, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Upload successful!")
            print(f"  📝 Transcription: {data.get('transcription', 'N/A')}")
            print(f"  📁 Filename: {data.get('filename', 'N/A')}")
            
            # Check if file was actually saved
            filename = data.get('filename')
            if filename:
                file_path = os.path.join('uploads', filename)
                if os.path.exists(file_path):
                    print(f"  ✅ File saved successfully: {file_path}")
                    print(f"  📊 File size: {os.path.getsize(file_path)} bytes")
                else:
                    print(f"  ❌ File not found: {file_path}")
                    return False
            
            return data
        else:
            print(f"❌ Upload failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def test_response_generation(transcription):
    """Test AI response generation"""
    print("\n🤖 Testing Response Generation")
    print("=" * 50)
    
    try:
        data = {'transcription': transcription}
        print(f"📤 Generating response for: '{transcription[:50]}...'")
        
        response = requests.post(f"{BASE_URL}/generate", data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Response generation successful!")
            print(f"  🤖 Generated response: {result.get('generated_response', 'N/A')}")
            return result
        else:
            print(f"❌ Response generation failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Response generation error: {e}")
        return False

def test_save_interaction(filename, transcription, generated_response, final_response, athlete_id=1):
    """Test saving the complete interaction"""
    print("\n💾 Testing Save Interaction")
    print("=" * 50)
    
    try:
        data = {
            'athlete_id': athlete_id,
            'filename': filename,
            'transcription': transcription,
            'generated_response': generated_response,
            'final_response': final_response,
            'category': 'Test',
            'priority': 'medium',
            'notes': 'Automated test interaction'
        }
        
        print(f"📤 Saving interaction for athlete {athlete_id}...")
        response = requests.post(f"{BASE_URL}/save", data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Interaction saved successfully!")
            print(f"  🆔 Record ID: {result.get('record_id', 'N/A')}")
            return result
        else:
            print(f"❌ Save failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Save error: {e}")
        return False

def test_history_retrieval(athlete_id=1):
    """Test retrieving athlete history"""
    print("\n📚 Testing History Retrieval")
    print("=" * 50)
    
    try:
        print(f"📤 Retrieving history for athlete {athlete_id}...")
        response = requests.get(f"{BASE_URL}/athletes/{athlete_id}/history", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            history = data.get('history', [])
            print(f"✅ History retrieved successfully!")
            print(f"  📊 Records found: {len(history)}")
            
            if history:
                latest = history[0]
                print(f"  🕒 Latest record: {latest.get('timestamp', 'N/A')}")
                print(f"  📝 Latest transcription: {latest.get('transcription', 'N/A')[:50]}...")
            
            return data
        else:
            print(f"❌ History retrieval failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ History retrieval error: {e}")
        return False

def run_complete_audio_workflow():
    """Run the complete audio processing workflow test"""
    print("🏆 Elite Athlete CRM - Complete Audio Workflow Test")
    print("=" * 60)
    
    # Step 1: Upload audio
    upload_result = test_audio_upload()
    if not upload_result:
        print("❌ Audio workflow test failed at upload step")
        return False
    
    # Step 2: Generate response
    transcription = upload_result.get('transcription', 'Test transcription for athlete coaching')
    response_result = test_response_generation(transcription)
    if not response_result:
        print("❌ Audio workflow test failed at response generation step")
        return False
    
    # Step 3: Save interaction
    filename = upload_result.get('filename', 'test_file.ogg')
    generated_response = response_result.get('generated_response', 'Generated test response')
    final_response = f"Final edited version: {generated_response}"
    
    save_result = test_save_interaction(filename, transcription, generated_response, final_response)
    if not save_result:
        print("❌ Audio workflow test failed at save step")
        return False
    
    # Step 4: Verify history
    history_result = test_history_retrieval()
    if not history_result:
        print("❌ Audio workflow test failed at history retrieval step")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Complete Audio Workflow Test PASSED!")
    print("All components are working correctly:")
    print("  ✅ Audio upload and file storage")
    print("  ✅ Transcription processing") 
    print("  ✅ AI response generation")
    print("  ✅ Interaction saving")
    print("  ✅ History retrieval")
    
    return True

if __name__ == "__main__":
    success = run_complete_audio_workflow()
    exit(0 if success else 1) 