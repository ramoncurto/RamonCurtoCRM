"""
Transcription service using OpenAI Whisper API for the dashboard.
This integrates the transcription functionality from bot.py into the FastAPI application.
"""

import os
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
import logging
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptionService:
    """
    Service for transcribing audio files using OpenAI Whisper API.
    """
    
    def __init__(self):
        """Initialize the transcription service with OpenAI client."""
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the OpenAI client."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("OPENAI_API_KEY not found in environment variables")
                self.client = None
                return
                
            self.client = AsyncOpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {e}")
            self.client = None
    
    def _convert_opus_to_wav(self, opus_path: str) -> Optional[str]:
        """
        Convert .opus file to .wav format using ffmpeg.
        
        Parameters
        ----------
        opus_path : str
            Path to the .opus file
            
        Returns
        -------
        Optional[str]
            Path to the converted .wav file or None if conversion fails
        """
        try:
            # Check if ffmpeg is available
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("FFmpeg not found. Please install FFmpeg to convert .opus files.")
                logger.error("Windows: Download from https://ffmpeg.org/download.html")
                logger.error("macOS: brew install ffmpeg")
                logger.error("Linux: sudo apt install ffmpeg")
                return None

            # Create temporary .wav file
            wav_path = opus_path.replace('.opus', '.wav')
            if not wav_path.endswith('.wav'):
                wav_path = wav_path + '.wav'
                
            # Use ffmpeg to convert opus to wav
            cmd = [
                'ffmpeg', '-i', opus_path, '-ar', '16000', '-ac', '1', '-y', wav_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully converted {opus_path} to {wav_path}")
                return wav_path
            else:
                logger.error(f"FFmpeg conversion failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting opus to wav: {e}")
            return None

    async def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file to text using OpenAI Whisper API.
        
        Parameters
        ----------
        audio_path : str
            Path to the audio file
            
        Returns
        -------
        Optional[str]
            Transcribed text or None if error
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return None
            
        try:
            # Convert to absolute path and verify file exists
            abs_path = os.path.abspath(audio_path)
            logger.info(f"Transcribing audio file: {abs_path}")
            
            if not os.path.exists(abs_path):
                logger.error(f"File does not exist: {abs_path}")
                return None
                
            # Check file size
            file_size = os.path.getsize(abs_path)
            logger.info(f"File size: {file_size} bytes")
            
            # Handle .opus files by converting to .wav
            final_path = abs_path
            if abs_path.lower().endswith('.opus'):
                logger.info("Converting .opus file to .wav format...")
                converted_path = self._convert_opus_to_wav(abs_path)
                if converted_path:
                    final_path = converted_path
                else:
                    logger.error("Failed to convert .opus file")
                    logger.error("To transcribe WhatsApp .opus files, please install FFmpeg:")
                    logger.error("Windows: Download from https://ffmpeg.org/download.html")
                    logger.error("macOS: brew install ffmpeg")
                    logger.error("Linux: sudo apt install ffmpeg")
                    return "[Error: .opus format not supported by OpenAI. Install FFmpeg for conversion or use mp3/wav files]"
            
            # Use OpenAI Whisper API for transcription
            with open(final_path, "rb") as f:
                result = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text"
                )
            
            transcription = result.strip()
            logger.info(f"Transcription completed: {len(transcription)} characters")
            
            # Clean up converted file if it was created
            if final_path != abs_path and os.path.exists(final_path):
                os.unlink(final_path)
                
            return transcription
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            logger.error(f"File path: {audio_path}")
            logger.error(f"Absolute path: {os.path.abspath(audio_path)}")
            logger.error(f"Current working directory: {os.getcwd()}")
            
            # Clean up converted file if it exists
            if 'final_path' in locals() and final_path != abs_path and os.path.exists(final_path):
                os.unlink(final_path)
                
            return None
    
    async def transcribe_audio_bytes(self, audio_bytes: bytes, file_extension: str = ".mp3") -> Optional[str]:
        """
        Transcribe audio from bytes using a temporary file.
        
        Parameters
        ----------
        audio_bytes : bytes
            Audio file content as bytes
        file_extension : str
            File extension for the temporary file
            
        Returns
        -------
        Optional[str]
            Transcribed text or None if error
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return None
            
        try:
            # Handle WhatsApp .opus files specifically
            if file_extension.lower() == ".opus":
                file_extension = ".opus"
                
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
                
            try:
                transcription = await self.transcribe_audio(temp_path)
                return transcription
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Error transcribing audio bytes: {e}")
            return None

# Global instance
transcription_service = TranscriptionService()
