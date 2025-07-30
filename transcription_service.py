"""
Servicio de transcripción mejorado usando OpenAI Whisper API
Soporta múltiples formatos de audio incluyendo WhatsApp/Telegram
"""

import os
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple
import logging
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptionService:
    """
    Servicio mejorado para transcribir archivos de audio usando OpenAI Whisper API.
    Soporta múltiples formatos incluyendo WhatsApp (.ogg, .opus) y Telegram (.m4a, .oga).
    """
    
    # Formatos de audio soportados que requieren conversión
    CONVERSION_FORMATS = {
        '.opus': 'opus',
        '.ogg': 'ogg',
        '.oga': 'ogg', 
        '.m4a': 'aac',
        '.aac': 'aac',
        '.webm': 'webm'
    }
    
    # Formatos directamente soportados por OpenAI Whisper
    DIRECT_FORMATS = {'.mp3', '.wav', '.flac', '.mp4', '.mpeg', '.mpga', '.m4a', '.webm'}
    
    def __init__(self):
        """Initialize the transcription service with OpenAI client."""
        self.client = None
        self.ffmpeg_available = False
        self._initialize_client()
        self._check_ffmpeg()
    
    def _initialize_client(self):
        """Initialize the OpenAI client with proper error handling."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("❌ OPENAI_API_KEY not found in environment variables")
                logger.error("💡 Please add OPENAI_API_KEY to your .env file")
                self.client = None
                return
                
            self.client = AsyncOpenAI(api_key=api_key)
            logger.info("✅ OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing OpenAI client: {e}")
            self.client = None
    
    def _check_ffmpeg(self):
        """Check if ffmpeg is available for audio conversion."""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'], 
                capture_output=True, 
                check=True,
                timeout=10
            )
            self.ffmpeg_available = True
            logger.info("✅ FFmpeg is available for audio conversion")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.ffmpeg_available = False
            logger.warning("⚠️  FFmpeg not found. Audio conversion will be limited.")
            logger.info("💡 Install FFmpeg:")
            logger.info("   Windows: Download from https://ffmpeg.org/download.html")
            logger.info("   macOS: brew install ffmpeg")
            logger.info("   Linux: sudo apt install ffmpeg")
    
    def _get_file_info(self, file_path: str) -> Tuple[str, int]:
        """
        Get file extension and size information.
        
        Returns:
            Tuple of (extension, file_size_bytes)
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        file_size = path.stat().st_size if path.exists() else 0
        return extension, file_size
    
    def _convert_audio_to_supported_format(self, input_path: str) -> Optional[str]:
        """
        Convert audio file to a format supported by OpenAI Whisper.
        
        Parameters
        ----------
        input_path : str
            Path to the input audio file
            
        Returns
        -------
        Optional[str]
            Path to the converted file or None if conversion fails
        """
        if not self.ffmpeg_available:
            logger.error("❌ FFmpeg not available for audio conversion")
            return None
            
        try:
            input_path = os.path.abspath(input_path)
            extension, file_size = self._get_file_info(input_path)
            
            logger.info(f"🔄 Converting {extension} file ({file_size} bytes) to WAV format...")
            
            # Create output path with .wav extension
            output_path = input_path.rsplit('.', 1)[0] + '_converted.wav'
            
            # FFmpeg command for high-quality conversion
            # Optimized for speech recognition
            cmd = [
                'ffmpeg',
                '-i', input_path,           # Input file
                '-ar', '16000',             # Sample rate 16kHz (optimal for Whisper)
                '-ac', '1',                 # Mono channel
                '-c:a', 'pcm_s16le',        # PCM 16-bit little-endian
                '-y',                       # Overwrite output file
                output_path
            ]
            
            # Run conversion with timeout
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                converted_size = os.path.getsize(output_path)
                logger.info(f"✅ Successfully converted to {output_path} ({converted_size} bytes)")
                return output_path
            else:
                logger.error(f"❌ FFmpeg conversion failed:")
                logger.error(f"   Command: {' '.join(cmd)}")
                logger.error(f"   Error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Audio conversion timed out (>5 minutes)")
            return None
        except Exception as e:
            logger.error(f"❌ Error converting audio: {e}")
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
            Transcribed text or detailed error message
        """
        if not self.client:
            return "❌ Error: OpenAI API not configured. Please add OPENAI_API_KEY to your environment."
            
        try:
            # Convert to absolute path and verify file exists
            abs_path = os.path.abspath(audio_path)
            logger.info(f"🎤 Transcribing audio file: {abs_path}")
            
            if not os.path.exists(abs_path):
                logger.error(f"❌ File does not exist: {abs_path}")
                return f"❌ Error: File not found - {abs_path}"
                
            # Get file information
            extension, file_size = self._get_file_info(abs_path)
            logger.info(f"📁 File info: {extension} format, {file_size:,} bytes")
            
            # Check file size (OpenAI limit is 25MB)
            if file_size > 25 * 1024 * 1024:
                return "❌ Error: File too large (>25MB). Please use a smaller audio file."
            
            if file_size == 0:
                return "❌ Error: File is empty or corrupted."
            
            # Determine if conversion is needed
            final_path = abs_path
            needs_cleanup = False
            
            if extension in self.CONVERSION_FORMATS:
                if not self.ffmpeg_available:
                    return f"❌ Error: {extension} format requires FFmpeg for conversion.\n" \
                           f"💡 Please install FFmpeg or use MP3/WAV files instead.\n" \
                           f"   Windows: Download from https://ffmpeg.org/download.html\n" \
                           f"   macOS: brew install ffmpeg\n" \
                           f"   Linux: sudo apt install ffmpeg"
                
                logger.info(f"🔄 Converting {extension} file...")
                converted_path = self._convert_audio_to_supported_format(abs_path)
                
                if not converted_path:
                    return f"❌ Error: Failed to convert {extension} file to supported format."
                
                final_path = converted_path
                needs_cleanup = True
            
            elif extension not in self.DIRECT_FORMATS:
                return f"❌ Error: Unsupported audio format '{extension}'.\n" \
                       f"💡 Supported formats: {', '.join(sorted(self.DIRECT_FORMATS | set(self.CONVERSION_FORMATS.keys())))}"
            
            # Transcribe using OpenAI Whisper API
            logger.info("🤖 Calling OpenAI Whisper API...")
            with open(final_path, "rb") as f:
                result = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text",
                    language=None  # Auto-detect language
                )
            
            transcription = result.strip()
            
            if transcription:
                logger.info(f"✅ Transcription completed: {len(transcription)} characters")
                logger.info(f"📝 Preview: {transcription[:100]}{'...' if len(transcription) > 100 else ''}")
            else:
                logger.warning("⚠️  Transcription returned empty result")
                transcription = "⚠️ Warning: Audio transcription returned empty result. The audio may be silent or unclear."
            
            # Clean up converted file if it was created
            if needs_cleanup and os.path.exists(final_path):
                os.unlink(final_path)
                logger.info(f"🗑️  Cleaned up temporary file: {final_path}")
                
            return transcription
            
        except Exception as e:
            logger.error(f"❌ Error transcribing audio: {e}")
            logger.error(f"   File path: {audio_path}")
            logger.error(f"   Absolute path: {abs_path}")
            logger.error(f"   Current working directory: {os.getcwd()}")
            
            # Clean up converted file if it exists
            if 'final_path' in locals() and 'needs_cleanup' in locals() and needs_cleanup:
                if os.path.exists(final_path):
                    os.unlink(final_path)
                    logger.info(f"🗑️  Cleaned up temporary file after error: {final_path}")
            
            # Return user-friendly error message
            if "Connection error" in str(e) or "timeout" in str(e).lower():
                return "❌ Error: Connection timeout. Please check your internet connection and try again."
            elif "authentication" in str(e).lower() or "api key" in str(e).lower():
                return "❌ Error: Invalid OpenAI API key. Please check your OPENAI_API_KEY configuration."
            elif "quota" in str(e).lower() or "billing" in str(e).lower():
                return "❌ Error: OpenAI API quota exceeded. Please check your OpenAI account billing."
            else:
                return f"❌ Error: Transcription failed - {str(e)}"
    
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
            Transcribed text or error message
        """
        if not self.client:
            return "❌ Error: OpenAI API not configured. Please add OPENAI_API_KEY to your environment."
        
        if not audio_bytes:
            return "❌ Error: No audio data provided."
            
        try:
            # Normalize extension
            if not file_extension.startswith('.'):
                file_extension = '.' + file_extension
            file_extension = file_extension.lower()
            
            logger.info(f"🎤 Transcribing audio bytes ({len(audio_bytes):,} bytes, {file_extension})")
            
            # Create temporary file
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
                    logger.info(f"🗑️  Cleaned up temporary file: {temp_path}")
                    
        except Exception as e:
            logger.error(f"❌ Error transcribing audio bytes: {e}")
            return f"❌ Error: Failed to process audio data - {str(e)}"
    
    def get_supported_formats(self) -> dict:
        """
        Get information about supported audio formats.
        
        Returns
        -------
        dict
            Dictionary with format information
        """
        return {
            "direct_formats": sorted(list(self.DIRECT_FORMATS)),
            "conversion_formats": sorted(list(self.CONVERSION_FORMATS.keys())),
            "ffmpeg_available": self.ffmpeg_available,
            "openai_configured": self.client is not None
        }
    
    def get_system_status(self) -> dict:
        """
        Get system status for troubleshooting.
        
        Returns
        -------
        dict
            System status information
        """
        return {
            "openai_api_configured": self.client is not None,
            "ffmpeg_available": self.ffmpeg_available,
            "supported_direct_formats": sorted(list(self.DIRECT_FORMATS)),
            "supported_conversion_formats": sorted(list(self.CONVERSION_FORMATS.keys())),
            "recommendations": self._get_recommendations()
        }
    
    def _get_recommendations(self) -> list:
        """Get system recommendations for better functionality."""
        recommendations = []
        
        if not self.client:
            recommendations.append({
                "type": "error",
                "message": "Configure OpenAI API key",
                "action": "Add OPENAI_API_KEY to your .env file"
            })
        
        if not self.ffmpeg_available:
            recommendations.append({
                "type": "warning", 
                "message": "Install FFmpeg for full format support",
                "action": "Install FFmpeg to support WhatsApp/Telegram audio formats (.ogg, .opus, .m4a)"
            })
        
        if self.client and self.ffmpeg_available:
            recommendations.append({
                "type": "success",
                "message": "System fully configured",
                "action": "All audio formats are supported"
            })
        
        return recommendations

# Global instance
transcription_service = TranscriptionService()
