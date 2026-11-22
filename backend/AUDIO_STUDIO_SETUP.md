# Audio Studio Setup Notes

## faster-whisper Installation

The Audio Studio uses `faster-whisper==1.1.0` for speech-to-text transcription.

### Known Issue: av Library Compatibility

**Problem:** faster-whisper 1.1.0 uses a parameter `metadata_errors="ignore"` in `av.open()` that is not supported by av 19.0.2 (the latest available version on some systems).

**Solution:** The `faster_whisper/audio.py` file must be patched to remove this parameter:

```bash
sed -i 's/metadata_errors="ignore"//g' /home/ubuntu/.local/lib/python3.12/site-packages/faster_whisper/audio.py
```

Or manually edit the file and change line 46 from:
```python
with av.open(input_file, mode="r", metadata_errors="ignore") as container:
```

To:
```python
with av.open(input_file, mode="r") as container:
```

**Note:** This patch is automatically applied during setup. If you reinstall faster-whisper, you'll need to reapply the patch.

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

# Test TTS
curl -X POST "http://localhost:8000/api/v1/audio/generate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "text=Hello world" \
  -F "voice_id=en-US-GuyNeural" \
  -F "pitch=1.0" \
  -F "rate=1.0" \
  -F "volume=1.0" \
  -F "output_format=mp3"

# Test STT
curl -X POST "http://localhost:8000/api/v1/audio/transcribe" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@test.mp3"
```
