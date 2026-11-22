# Audio Studio Setup Notes

## faster-whisper Installation

The Audio Studio uses `faster-whisper==1.1.0` for speech-to-text transcription.

### No Patches Required

The audio transcription system decodes audio files internally using Python's `wave` module and NumPy, bypassing faster-whisper's av decoder entirely. This eliminates any compatibility issues between faster-whisper and the av library. Simply install the packages from requirements.txt and you're ready to go.

## Whisper Model Download

### Model Details
- **Model used:** `tiny` (default, configurable via `WHISPER_MODEL_SIZE` env var)
- **Size:** ~75MB
- **Cache location:** `~/.cache/huggingface/hub/`
- **Download:** Automatic on first transcription request
- **Device:** CPU with int8 quantization for optimal performance

### Model Sizes Available
- `tiny`: ~75MB (fastest, good for real-time)
- `base`: ~145MB (better accuracy)
- `small`: ~466MB (better accuracy)
- `medium`: ~1.5GB (high accuracy)
- `large`: ~3GB (highest accuracy)

For CPU-only systems, we recommend `tiny` or `base` models.

## FFmpeg Requirement

FFmpeg is required for:
1. Audio format conversion (MP3/WebM/etc → WAV)
2. Audio resampling to 16kHz mono

### Installation
**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
```bash
# Option 1: Using winget (Windows 10+)
winget install Gyan.FFmpeg

# Option 2: Using Chocolatey
choco install ffmpeg
```

Or download from: https://ffmpeg.org/download.html

The backend will automatically check for ffmpeg and return a clear error message if it's missing.

## Supported Audio Formats

### Input (STT - Speech-to-Text)
- MP3 (audio/mpeg)
- WAV (audio/wav)
- WebM (audio/webm) - browser MediaRecorder output
- Any format supported by ffmpeg

All formats are automatically converted to WAV 16kHz mono before transcription.

### Output (TTS - Text-to-Speech)
- MP3 (default)
- WAV

## CPU-Only Compatibility

✅ Both TTS and STT are fully CPU-compatible:

**edge-tts (TTS):**
- Uses Microsoft's cloud API
- No local model loading
- No GPU required

**faster-whisper (STT):**
- CTranslate2 backend optimized for CPU
- int8 quantization for better performance
- Automatically detects and uses CPU when no GPU available
- Performance: ~1-2x realtime on modern CPUs with tiny model

## Testing

Run the following to verify setup:

```bash
# Check ffmpeg
ffmpeg -version

# Test TTS (generates English audio)
curl -X POST "http://localhost:8000/api/v1/audio/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "text=Hello world" \
  -F "voice_id=en-US-GuyNeural" \
  -F "pitch=1.0" \
  -F "rate=1.0" \
  -F "volume=1.0" \
  -F "output_format=mp3"

# Test STT (transcribes audio, auto-detects language)
curl -X POST "http://localhost:8000/api/v1/audio/transcribe" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@test.mp3"
```

### Supported Languages

**TTS:** English (US, India, UK), Hindi, Telugu  
**STT:** Auto-detects from 99+ languages including English, Hindi, Telugu, and all major Indian languages
