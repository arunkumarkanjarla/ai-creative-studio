# Audio Activity Feature - Testing Guide

## Implementation Complete ✅

All 4 phases of the Audio Activity feature have been implemented and pushed to branch `cursor/instant-preview-samples-0cfb`.

## What Was Implemented

### Phase 1: Backend Guest Access ✅
**Files Modified:**
- `backend/app/api/v1/audio.py` - All endpoints updated for optional auth
- `backend/app/db/migrations.py` - Idempotent migration for audio_events table

**Features:**
- ✅ All audio endpoints work with optional authentication (guests + signed-in users)
- ✅ Ownership model: users by `user_id`, guests by `visitor_id`
- ✅ Cross-visitor access returns 404 for security
- ✅ Custom voices require authentication (401 with clear message)
- ✅ Guest rate limits: 50/hour for generate and transcribe
- ✅ Guest content limits: 1000 chars for TTS, 10MB for STT
- ✅ User limits: 5000 chars for TTS, 50MB for STT
- ✅ Comprehensive event logging with `log_audio_event` for all actions
- ✅ POST `/api/v1/audio/events` endpoint for client-side play/download logging
- ✅ Idempotent migration for `audio_events` table with indexes

### Phase 2: Frontend Guest Access ✅
**Files Modified:**
- `apps/web/src/pages/Studios/AudioStudio.tsx` - Guest access and event logging
- `apps/web/src/components/Sidebar.tsx` - Show Audio Studio in guest mode

**Features:**
- ✅ Audio Studio works for guests (no sign-in required)
- ✅ X-Visitor-Id sent with all requests (already implemented)
- ✅ Bearer token sent only when exists (already conditional)
- ✅ Log play and download events via POST `/api/v1/audio/events`
- ✅ Prompt guests to sign in for custom voices with confirm dialog
- ✅ Show different character limits for guests (1000) vs users (5000)
- ✅ Updated `fetchAuthenticatedMedia` to work for both guests and users
- ✅ Pass metadata to play/download events in all UI locations

### Phase 3: Admin API ✅
**Files Modified:**
- `backend/app/api/v1/analytics.py` - 5 new admin endpoints

**Admin Endpoints (all behind `require_admin`):**

1. **GET `/api/v1/analytics/audio/summary`** - Summary stats and charts data
   - Total events, success/failed/rate-limited counts
   - TTS vs STT, authenticated vs guest breakdown
   - Unique users and visitors
   - Total characters and minutes processed
   - Top voices and languages
   - Time series data (daily)

2. **GET `/api/v1/analytics/audio/events`** - Filterable events log with pagination
   - Filters: date range, user_type, user_id, visitor_id, action, status, voice, language, search
   - Returns full event details with user emails
   - Limit 1000 per page

3. **GET `/api/v1/analytics/audio/users`** - Users and guests list with activity stats
   - Per-action counts (TTS, STT, play, download)
   - Total characters and minutes
   - Top voices and languages used
   - First/last seen timestamps
   - Filter by user_type (authenticated/guest)

4. **GET `/api/v1/analytics/audio/timeline/{identifier}?user_type=...`** - Per-person detailed timeline
   - For both authenticated users (by user_id) and guests (by visitor_id)
   - Full event history with metadata
   - Pagination support

5. **GET `/api/v1/analytics/audio/events/csv`** - CSV export with filters
   - All event fields exported
   - User emails included for authenticated users
   - Same filters as events endpoint

### Phase 4: Admin UI ✅
**Files Created/Modified:**
- `apps/web/src/pages/Admin/AudioActivity.tsx` - New admin page (new file)
- `apps/web/src/App.tsx` - Route added
- `apps/web/src/components/Sidebar.tsx` - Menu item added
- `apps/web/src/App.css` - Styles added

**Features:**
- ✅ New Audio Activity page at `/admin/audio-activity`
- ✅ Summary cards: total events, users/guests, TTS/STT, processing stats
- ✅ Charts:
  - Activity over time (line chart: TTS vs STT)
  - Signed-in vs Guest (bar chart)
  - Top voices (list)
  - Top languages (list)
- ✅ Three tabs:
  1. **Users & Guests table** - Per-action counts, characters, minutes, top voices/languages
  2. **Events Log** - Filters (user type, action, status, search) and CSV export
  3. **Per-person timeline** - Detailed event history with full metadata
- ✅ Date range selector (today, 7d, 30d, custom)
- ✅ Pagination for all tables
- ✅ Timeline shows input text, audio details, device info, errors
- ✅ Added to sidebar under Analytics section
- ✅ Responsive design with mobile support
- ✅ Styled with status badges, action badges, and data tables

## Commits

1. **b3294d3** - Phase 1: Add guest access to all audio endpoints
2. **56281b7** - Phase 2: Frontend guest access and event logging
3. **3438e41** - Phase 3: Add comprehensive Audio Activity admin API
4. **c5fe5bd** - Phase 4: Add Audio Activity admin UI

## How to Test

### Prerequisites
1. PostgreSQL database running
2. Backend dependencies installed: `pip install -r backend/requirements.txt`
3. Frontend dependencies installed: `cd apps/web && npm install`
4. Environment variables set in `backend/.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/ai_creative_studio
   JWT_SECRET_KEY=your-secret-key
   ```

### Test 1: Guest TTS (No Authentication)
```bash
# Start backend
cd backend
python -m uvicorn app.main:app --reload

# Test TTS without authentication
curl -X POST http://localhost:8000/api/v1/audio/generate \
  -H "X-Visitor-Id: test-guest-123" \
  -F "text=Hello world" \
  -F "voice_id=en-US-AriaNeural" \
  -F "pitch=1.0" \
  -F "rate=1.0" \
  -F "volume=1.0" \
  -F "output_format=mp3"

# Should return: {"id": 1, "status": "completed", "file_url": "...", ...}
```

### Test 2: Guest STT (No Authentication)
```bash
# Transcribe audio without authentication
curl -X POST http://localhost:8000/api/v1/audio/transcribe \
  -H "X-Visitor-Id: test-guest-123" \
  -F "audio=@test.mp3"

# Should return: {"id": 1, "status": "completed", "text": "...", ...}
```

### Test 3: Cross-Visitor Access Returns 404
```bash
# Try to download with different visitor ID
curl -X GET http://localhost:8000/api/v1/audio/download/1 \
  -H "X-Visitor-Id: different-visitor-456"

# Should return: 404 "Audio not found"
```

### Test 4: Check audio_events Table
```sql
-- Connect to PostgreSQL
psql -U user -d ai_creative_studio

-- Check event logs
SELECT 
  id, action, status, 
  user_id, visitor_id, 
  voice_name, language, 
  text_length, audio_duration, 
  processing_time_ms, 
  created_at 
FROM audio_events 
ORDER BY created_at DESC 
LIMIT 10;
```

Expected columns in audio_events:
- `id`, `user_id`, `visitor_id`, `ip_address`
- `user_agent`, `browser`, `os`, `device`
- `action`, `studio`, `voice_id`, `voice_name`, `language`
- `text_length`, `input_text`, `audio_duration`, `file_size`
- `processing_time_ms`, `status`, `error_message`
- `generation_id`, `transcription_id`, `created_at`

### Test 5: Frontend (Signed Out)
```bash
# Start frontend
cd apps/web
npm run dev

# Navigate to http://localhost:5173/studios/audio
# Should see Audio Studio without being logged in
# Try generating TTS with 1000 character limit message
# Try playing and downloading audio
```

### Test 6: Frontend (Signed In)
```bash
# Log in as a user
# Navigate to http://localhost:5173/studios/audio
# Should see Audio Studio with 5000 character limit
# Generate TTS and check that it logs properly
```

### Test 7: Admin Audio Activity Page
```bash
# Log in as admin user (role = "systemadministrator")
# Navigate to http://localhost:5173/admin/audio-activity

# Should see:
# - Summary cards with metrics
# - Charts (Activity over time, Signed-in vs Guest, Top voices, Top languages)
# - Users & Guests tab with table
# - Events Log tab with filters
# - Ability to view per-person timeline
# - CSV export button
```

### Test 8: Rate Limiting
```bash
# Make 51 TTS requests as a guest within an hour
for i in {1..51}; do
  curl -X POST http://localhost:8000/api/v1/audio/generate \
    -H "X-Visitor-Id: test-guest-123" \
    -F "text=Test $i" \
    -F "voice_id=en-US-AriaNeural" \
    -F "pitch=1.0" \
    -F "rate=1.0" \
    -F "volume=1.0" \
    -F "output_format=mp3"
done

# 51st request should return: 429 "Rate limit exceeded..."
```

### Test 9: Admin API Endpoints
```bash
# Get admin token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"adminpass"}' | jq -r .access_token)

# Get summary
curl -X GET "http://localhost:8000/api/v1/analytics/audio/summary?start_date=2024-01-01T00:00:00&end_date=2024-12-31T23:59:59" \
  -H "Authorization: Bearer $TOKEN"

# Get events log
curl -X GET "http://localhost:8000/api/v1/analytics/audio/events?limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN"

# Get users list
curl -X GET "http://localhost:8000/api/v1/analytics/audio/users" \
  -H "Authorization: Bearer $TOKEN"

# Get user timeline
curl -X GET "http://localhost:8000/api/v1/analytics/audio/timeline/1?user_type=authenticated" \
  -H "Authorization: Bearer $TOKEN"

# Export CSV
curl -X GET "http://localhost:8000/api/v1/analytics/audio/events/csv" \
  -H "Authorization: Bearer $TOKEN" > audio_events.csv
```

## Expected Evidence

### 1. Guest TTS Working
Screenshot showing Audio Studio working while signed out, with generated audio

### 2. Guest STT Working
Screenshot showing transcription working while signed out

### 3. Cross-Visitor 404
Terminal showing 404 error when trying to access another visitor's audio

### 4. audio_events Table Rows
SQL query results showing populated event rows with all fields:
```
 id | user_id | visitor_id | action | status | voice_name | text_length | duration | ...
----+---------+------------+--------+--------+------------+-------------+----------+----
  1 |    NULL | guest-123  | generate | success | Aria (US) |     45     |   2.3    | ...
  2 |      5  | NULL       | play     | success | Guy (US)  |     NULL   |   1.5    | ...
```

### 5. Admin Audio Activity Page Screenshots
- Summary cards with real data
- Charts populated with event data
- Users table showing both authenticated users and guests
- Events log with filters working
- Timeline view for a specific user/guest
- CSV export downloading

### 6. Clean Build
```bash
cd apps/web
npm run build
# Should complete without errors
```

## Database Schema

The `audio_events` table includes these indexed columns:
- `user_id` (nullable, indexed) - For authenticated users
- `visitor_id` (nullable, indexed) - For guests
- `ip_address` (INET) - User IP address
- `action` (indexed) - generate, transcribe, play, download, etc.
- `status` (indexed) - success, failed, rate_limited
- `voice_name`, `language` - Audio details
- `text_length`, `audio_duration`, `file_size` - Content metrics
- `processing_time_ms` - Performance tracking
- `error_message` - Failure details
- `generation_id`, `transcription_id` - References to audio items
- `created_at` (indexed) - Timestamp

Migrations are idempotent - safe to run multiple times.

## Code Quality

- ✅ All endpoints use proper error handling
- ✅ Rate limiting with clear error messages
- ✅ Security: 404 for unauthorized access (not 403, to avoid enumeration)
- ✅ Logging doesn't fail the main operation
- ✅ Frontend handles both authenticated and guest states
- ✅ Responsive design for mobile
- ✅ Pagination for large datasets
- ✅ CSV export for data analysis
- ✅ Comprehensive filtering and search
- ✅ Clean separation of concerns

## Notes

- The implementation is production-ready
- All migrations are idempotent (safe for existing databases)
- Guest rate limits are configurable via `check_rate_limit` parameters
- Content limits are clearly communicated to users
- Event logging is non-blocking (failures don't break the main operation)
- Admin endpoints require `role == "systemadministrator"`
- Timeline supports both users (by user_id) and guests (by visitor_id)
