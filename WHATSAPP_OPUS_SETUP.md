# WhatsApp .opus Audio File Transcription Setup

## Issue
WhatsApp voice messages are saved as `.opus` files, but OpenAI's Whisper API doesn't support this format directly. The supported formats are: `['flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']`

## Solution
We need to convert `.opus` files to a supported format using FFmpeg.

## Installation Instructions

### Windows
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add FFmpeg to your PATH:
   - Open System Properties → Advanced → Environment Variables
   - Add `C:\ffmpeg\bin` to your PATH variable
4. Restart your terminal/command prompt

### macOS
```bash
brew install ffmpeg
```

### Linux
```bash
sudo apt update
sudo apt install ffmpeg
```

## Verification
After installation, verify FFmpeg is working:
```bash
ffmpeg -version
```

## Alternative Solutions
If you cannot install FFmpeg:

1. **Use a different audio format**: Ask users to send audio in supported formats
2. **Use a cloud conversion service**: Implement conversion via external API
3. **Use local Whisper model**: Switch back to local Whisper which supports .opus

## Current Behavior
- The system will attempt to convert .opus files to .wav using FFmpeg
- If FFmpeg is not available, it will log clear instructions
- Other formats (mp3, wav, ogg, etc.) work directly with OpenAI's API
