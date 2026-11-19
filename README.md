# AI Creative Studio

Monorepo for web, mobile, and backend creative AI tools.

## Voice Input Setup

Voice input works in Chrome/Edge using the Web Speech API. For Firefox/Safari or when the speech service is unavailable, the app falls back to recording with MediaRecorder and transcribing via the backend.

### Browser Support

- **Chrome/Edge**: Built-in Web Speech API (no backend needed)
- **Firefox/Safari**: MediaRecorder → Backend Whisper transcription

### Backend Transcription (Optional)

To enable fallback transcription for Firefox/Safari:

1. Install faster-whisper (optional dependency):
   ```bash
   cd backend
   pip install faster-whisper
   ```

2. The transcription endpoint (`/api/v1/transcribe`) will automatically use Whisper when available.

3. Configure model size (optional):
   ```bash
   export WHISPER_MODEL_SIZE=tiny  # tiny, base, small, medium, large
   ```

**Note:** If faster-whisper is not installed, the fallback will return a helpful error message and voice input will only work in Chrome/Edge.

### Supported Languages

- English (US, India)
- Hindi, Telugu, Tamil, Marathi, Bengali, Gujarati, Kannada, Malayalam

### Permissions

Voice input requires microphone access:
- First click prompts for permission
- Click the lock icon in address bar → Site permissions → Microphone → Allow
- Reload page after changing permissions
