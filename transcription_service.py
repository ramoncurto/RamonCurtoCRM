"""
Transcription service using Whisper model for the dashboard.
This integrates the transcription functionality from bot.py into the FastAPI application.
"""

import os
import whisper
import tempfile
from pathlib import Path
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptionService:
    """
    Service for transcribing audio files using Whisper model.
    """
    
    def __init__(self):
        """Initialize the transcription service with Whisper model."""
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model."""
        try:
            logger.info("Loading Whisper model...")
            self.model = whisper.load_model("small")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            self.model = None
    
    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file to text using Whisper.
        
        Parameters
        ----------
        audio_path : str
            Path to the audio file
            
        Returns
        -------
        Optional[str]
            Transcribed text or None if error
        """
        if not self.model:
            logger.error("Whisper model not loaded")
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
            
            # Transcribe with absolute path
            result = self.model.transcribe(abs_path)
            transcription = result["text"].strip()
            logger.info(f"Transcription completed: {len(transcription)} characters")
            return transcription
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            logger.error(f"File path: {audio_path}")
            logger.error(f"Absolute path: {os.path.abspath(audio_path)}")
            logger.error(f"Current working directory: {os.getcwd()}")
            return None
    
    def transcribe_audio_bytes(self, audio_bytes: bytes, file_extension: str = ".mp3") -> Optional[str]:
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
        if not self.model:
            logger.error("Whisper model not loaded")
            return None
            
        try:
            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
                
            try:
                transcription = self.transcribe_audio(temp_path)
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
