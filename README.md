# AI Creative Studio

Monorepo for web, mobile, and backend creative AI tools.

## Setup Instructions

### Database Migration (Windows)

To create the analytics tables locally:

```bash
# In backend directory
cd backend

# Ensure .env file has DATABASE_URL and JWT_SECRET_KEY
# Example: DATABASE_URL=postgresql://user:password@localhost:5432/ai_creative_studio

# Install dependencies if not already done
pip install -r requirements.txt

# Create all tables (including new analytics tables)
python -c "from app.db.database import engine; from app.db.base import Base; Base.metadata.create_all(bind=engine)"
```

Tables created:
- `visitor_sessions` - Page visits and visitor tracking
- `login_sessions` - Login history and authentication events
- `usage_events` - Studio usage and generation events

## Voice Input

Voice input works in Chrome/Edge using the Web Speech API. Firefox/Safari can use MediaRecorder with backend transcription.

### Quick Start

**Chrome/Edge (Built-in):**
- Click microphone button
- Allow microphone permission when prompted
- Start speaking

**Firefox/Safari (Requires backend):**
```bash
cd backend
pip install faster-whisper
# Optional: export WHISPER_MODEL_SIZE=tiny
```

### Common Issues

| Error | Solution |
|-------|----------|
| No microphone found | Connect a mic or headset, app auto-detects when plugged in |
| Permission denied | Click lock icon → Site permissions → Microphone → Allow, then Retry |
| In use by another app | Close other apps using microphone |
| Requires HTTPS | Use localhost or HTTPS for voice input |

### Supported Languages
English (US, India), Hindi, Telugu, Tamil, Marathi, Bengali, Gujarati, Kannada, Malayalam

### Device Detection
The app automatically detects when microphones are connected/disconnected and updates the mic button state.
