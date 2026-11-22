# AI Creative Studio - Project Architecture Overview

## Project Structure

This is a monorepo containing a React frontend (Vite + TypeScript) and Python FastAPI backend.

```
ai-creative-studio/
├── apps/
│   ├── web/              # React frontend (Vite + TypeScript)
│   └── mobile/           # Mobile app (not covered in this overview)
├── backend/              # Python FastAPI backend
├── .gitignore
└── README.md
```

## Frontend (`apps/web/`)

### Tech Stack
- **Framework**: React 19.3.1
- **Build Tool**: Vite 8.3.8
- **Language**: TypeScript 7.0.2
- **Routing**: React Router DOM 7.18.5
- **Icons**: Lucide React 1.73.0
- **Styling**: Plain CSS with CSS variables (theme system)

### Directory Structure

```
apps/web/src/
├── components/           # Reusable UI components
│   ├── AdminRoute.tsx
│   ├── AuthFooter.tsx
│   ├── GenerationProgress.tsx  # Progress bar for AI generation
│   ├── Navbar.tsx
│   ├── ProtectedRoute.tsx
│   ├── Sidebar.tsx
│   └── ThemePicker.tsx
├── context/              # React Context providers
│   ├── AuthContext.tsx   # User authentication state
│   └── ThemeContext.tsx  # Theme selection (multiple color themes)
├── pages/                # Page components (routes)
│   ├── Admin/            # Admin-only pages
│   │   ├── AIAccessSettings.tsx
│   │   ├── ImageHistory.tsx
│   │   └── ReferenceList.tsx
│   ├── Studios/          # Creative studio pages (main features)
│   │   ├── ImageStudio.tsx        # Image generation studio (main screen)
│   │   ├── AudioStudio.tsx        # Audio generation studio
│   │   ├── VideoStudio.tsx        # Video generation studio
│   │   └── photoStudioConfig.ts   # Config for Image Studio tools, styles, scenes
│   ├── Users/            # User management pages
│   │   ├── CreateUser.tsx
│   │   ├── EditUser.tsx
│   │   └── UserList.tsx
│   ├── Dashboard.tsx     # User dashboard
│   ├── Home.tsx          # Landing page
│   ├── Login.tsx
│   └── Register.tsx
├── services/             # API integration
│   ├── api.ts            # Base API client (fetch wrapper)
│   └── auth.ts           # Authentication service
├── theme/
│   └── themes.ts         # Theme definitions (color palettes)
├── App.css               # Global styles
├── App.tsx               # Main app component with routing
├── index.css             # Base CSS resets
└── main.tsx              # Entry point
```

### Key Frontend Pages

#### 1. **Image Studio** (`/studios/image?tool=text_to_image`)
The main image generation screen with:
- **Tool selection**: Text-to-Image, Image-to-Image, Person in Scene, Face Swap, etc.
- **Prompt input**: User describes what they want
- **Settings sidebar**:
  - Image Dimensions (1:1, 3:4, 4:3, 16:9)
  - Photo Type (Passport, ID Card, Album, Social, Poster)
  - Photo Style (Realistic, Cinematic, Natural, Studio, Vintage, Wedding, Fashion, Headshot)
  - Scene & Theme (Beach, Mountain, Waterfall, City, Temple, Garden, Wedding, Festival, Indoor, Custom)
- **Live Preview**: Shows instant sample or generated image
- **Actions**: Preview (fast sample) and Generate (full AI generation)

#### 2. **Dashboard** (`/dashboard`)
User's main hub showing:
- Quick access to Image, Audio, Video studios
- Recent generations
- Studio tools grid

#### 3. **Admin Pages** (`/admin/*`)
- Image History: View all generated images
- AI Access Settings: Configure generation limits
- Reference List: Manage reference style packs

### Frontend Routing

Routes are defined in `App.tsx`:
- `/` - Home page (landing)
- `/login`, `/register` - Authentication
- `/dashboard` - User dashboard
- `/studios/image`, `/studios/audio`, `/studios/video` - Creative studios
- `/users/*` - User management (admin only)
- `/admin/*` - Admin pages

### Theme System

The app supports multiple color themes via CSS variables:
- Theme picker in the UI
- Theme state managed by `ThemeContext`
- Themes defined in `theme/themes.ts`
- CSS variables in `:root` dynamically updated (e.g., `--bg-card`, `--accent`, `--text-primary`)

## Backend (`backend/`)

### Tech Stack
- **Framework**: FastAPI
- **Database**: SQLAlchemy ORM
- **Authentication**: JWT tokens
- **AI**: Custom image generation service (Stable Diffusion models)

### Directory Structure

```
backend/
├── app/
│   ├── api/v1/           # API endpoints
│   │   ├── auth.py       # Login, register, token refresh
│   │   ├── users.py      # User CRUD operations
│   │   ├── images.py     # Image generation endpoints
│   │   ├── ai_access.py  # AI access control
│   │   └── preview.py    # Sample preview endpoints (NEW)
│   ├── core/
│   │   ├── config.py     # App configuration
│   │   └── security.py   # Password hashing, JWT handling
│   ├── db/
│   │   ├── database.py   # Database connection
│   │   └── base.py       # Base model
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── generated_image.py
│   │   ├── generated_audio.py
│   │   ├── generated_video.py
│   │   └── ai_access.py
│   ├── schemas/          # Pydantic schemas (request/response models)
│   │   ├── user.py
│   │   ├── generated_image.py
│   │   └── ai_access.py
│   ├── services/         # Business logic
│   │   ├── ai/
│   │   │   ├── image_service.py     # Core image generation
│   │   │   ├── image_sizes.py
│   │   │   ├── job_progress.py      # Track generation jobs
│   │   │   ├── model_manager.py     # Load AI models
│   │   │   ├── prompt_builder.py
│   │   │   ├── prompt_intent.py
│   │   │   ├── prompt_store.py      # Reference style packs
│   │   │   └── background_mask.py
│   │   ├── access_control.py        # Rate limiting
│   │   └── user_service.py
│   └── main.py           # FastAPI app initialization
├── scripts/              # Utility scripts
│   ├── create_admin.py
│   └── test_image_generation.py
├── preview_images/       # Sample preview images (NEW)
│   ├── manifest.json     # Image metadata, licenses, credits
│   └── *.jpg             # 22 sample images
├── download_samples.py   # Script to download preview samples (NEW)
├── generated_images/     # AI-generated images (git-ignored)
├── reference_images/     # User-uploaded reference styles (git-ignored)
├── requirements.txt      # Python dependencies
└── sql/                  # Database schema
```

### Key Backend Endpoints

#### Authentication (`/api/v1/`)
- `POST /login` - User login (returns JWT token)
- `POST /register` - User registration
- `GET /users/me` - Get current user

#### Image Generation (`/api/v1/images/`)
- `POST /generate` - Start image generation job (async)
  - Accepts: prompt, tool, width, height, style, scene, photo_type, reference images
  - Returns: job_id
- `GET /jobs/{job_id}` - Poll generation progress (0-100%)
  - Returns: status, progress, message, image_url (when complete)
- `GET /history` - List user's generated images
- `GET /admin/history` - Admin: view all images
- `DELETE /{image_id}` - Admin: delete image

#### Preview Samples (`/api/v1/preview/`) **NEW**
- `GET /sample?style=X&scene=Y&photo_type=Z` - Get best-matching sample preview
  - Returns: `preview_url`, `key`, `photographer`, `source`
- `GET /manifest` - Full manifest of all sample images

#### Reference Styles (`/api/v1/images/prompts/`)
- `GET /prompts` - List saved style packs
- `POST /prompts` - Upload new reference style
- `DELETE /prompts/{id}` - Delete style pack

### How Images Are Served

1. **Generated Images**: 
   - Saved to `backend/generated_images/`
   - Served via `/generated` static mount
   - Example: `http://localhost:8000/generated/image_123.png`

2. **Reference Images**:
   - Saved to `backend/reference_images/<prompt_id>/`
   - Served via `/reference` static mount
   - Example: `http://localhost:8000/reference/abc123/ref.jpg`

3. **Preview Samples** **NEW**:
   - Committed to `backend/preview_images/`
   - Served via `/preview` static mount
   - Example: `http://localhost:8000/preview/realistic.jpg`

### Image Generation Flow

1. **Frontend** calls `POST /api/v1/images/generate` with prompt + settings
2. **Backend** creates `GeneratedImage` record with `status="processing"`
3. **Background thread** runs image generation:
   - Loads AI model (lazy-loaded on first use)
   - Applies prompt builder with style/scene/type hints
   - Generates image using Stable Diffusion
   - Saves to `generated_images/`
   - Updates database with `image_url`, `status="completed"`
4. **Frontend** polls `GET /api/v1/images/jobs/{job_id}` for progress
5. **Frontend** displays result when `status="completed"`

### Database Models

- **User**: User accounts (email, password_hash, role)
- **GeneratedImage**: Generated images (prompt, image_path, status, user_id)
- **GeneratedAudio**: Generated audio files
- **GeneratedVideo**: Generated videos
- **AIGenerationAttempt**: Track generation attempts for rate limiting

### Access Control

- **Guest users**: Can only use text_to_image
- **Logged-in users**: Full access to all studio tools
- **System administrators**: Access to admin pages, user management, history

## API Integration

The frontend communicates with the backend via:
- **Base URL**: `http://localhost:8000/api/v1/` (dev) or configured backend URL
- **Authentication**: JWT tokens in `Authorization: Bearer <token>` header
- **Helper**: `services/api.ts` provides `apiRequest<T>()` wrapper

Example:
```typescript
const result = await apiRequest<JobStartResponse>("/images/generate", {
  method: "POST",
  body: formData
});
```

## Development Workflow

### Frontend Dev Server
```bash
cd apps/web
npm install
npm run dev
# Runs on http://localhost:5173
```

### Backend Dev Server
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# Runs on http://localhost:8000
```

### Production Build
```bash
# Frontend
cd apps/web
npm run build  # Output: dist/

# Backend
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Key Features for Future Work

### Multi-Studio Architecture
The app is designed to support multiple creative studios:
- **Image Studio**: Text-to-image, image editing, face tools
- **Audio Studio**: Audio generation
- **Video Studio**: Video generation

Each studio follows a similar pattern:
1. Tool selection
2. Input (prompt + uploads)
3. Settings sidebar
4. Live preview/result area
5. Generate button → background job → poll progress → display result

### Extensibility Points

1. **New Tools**: Add to `CREATE_TOOLS` in `photoStudioConfig.ts`
2. **New Styles/Scenes**: Add to `PHOTO_STYLES` / `SCENES` arrays
3. **New Themes**: Add to `themes.ts`
4. **New API Endpoints**: Add router to `backend/app/api/v1/`
5. **New Models**: Add ORM model to `backend/app/models/`

### Recent Changes (This PR)

- Added **instant sample previews** to Image Studio
- Created `backend/preview_images/` with 22 sample images
- New `/api/v1/preview/sample` endpoint
- Made Live Preview compact and aspect-aware
- Sample images are committed to git (not generated)

## Configuration Files

- **Frontend**: `apps/web/package.json`, `apps/web/tsconfig.json`, `apps/web/vite.config.ts`
- **Backend**: `backend/requirements.txt`, `backend/app/core/config.py`
- **Git**: `.gitignore` (excludes generated_images, reference_images, but NOT preview_images)

## Next Steps for Future Work

Based on this architecture, future enhancements could include:
- Adding more sample images or video previews
- Expanding Audio and Video studios with similar instant preview features
- Building a design system component library
- Adding real-time progress updates via WebSockets
- Implementing image-to-video or style transfer tools
- Creating a mobile-responsive version of the studios
- Adding collaborative features (shared projects, comments)
