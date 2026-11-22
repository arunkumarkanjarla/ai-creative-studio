
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import time

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.images import router as images_router
from app.api.v1.ai_access import router as ai_access_router
from app.api.v1.preview import router as preview_router
from app.api.v1.transcribe import router as transcribe_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.audio import router as audio_router
from app.db.database import SessionLocal, engine, Base
from app.core.analytics import track_page_visit, get_client_ip
from app.core.security import decode_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Import all models to ensure they're registered with Base
    from app.models.user import User
    from app.models.generated_image import GeneratedImage
    from app.models.ai_access import AIGenerationAttempt
    from app.models.analytics import VisitorSession, LoginSession, UsageEvent
    from app.models.audio import VoiceProfile, TTSGeneration, Transcription
    
    # Create all tables if they don't exist
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Database tables ready.")
    
    yield
    
    # Cleanup on shutdown (if needed)
    print("Shutting down...")


# Do NOT load AI models here.
# Image model loads lazily on the first /images/generate request.
app = FastAPI(
    title="AI Creative Studio API",
    description="Open-source AI image, audio and video generation platform",
    version="1.0.0",
    lifespan=lifespan,
)


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Track visitor sessions for every API request."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip tracking for certain paths
        path = request.url.path
        skip_patterns = [
            "/preview/",
            "/generated/",
            "/reference/",
            "/docs",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/analytics/",
        ]
        
        should_skip = any(path.startswith(pattern) for pattern in skip_patterns)
        
        if not should_skip and path.startswith("/api/"):
            # Extract tracking data
            visitor_id = request.headers.get("X-Visitor-Id")
            user_agent = request.headers.get("User-Agent")
            forwarded_for = request.headers.get("X-Forwarded-For")
            ip = get_client_ip(request, forwarded_for)
            
            # Extract user_id from bearer token if present
            user_id = None
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]
                try:
                    payload = decode_token(token)
                    user_id = int(payload.get("sub")) if payload.get("sub") else None
                except Exception:
                    pass
            
            # Derive studio from route
            studio = None
            if "/images/" in path:
                studio = "image"
            elif "/audio/" in path:
                studio = "audio"
            elif "/video/" in path:
                studio = "video"
            
            # Track in background with own DB session
            if visitor_id:
                try:
                    db = SessionLocal()
                    try:
                        track_page_visit(
                            db=db,
                            visitor_id=visitor_id,
                            user_id=user_id,
                            ip=ip,
                            user_agent=user_agent,
                            path=path,
                            studio=studio,
                        )
                    finally:
                        db.close()
                except Exception as e:
                    print(f"[AnalyticsMiddleware] Error: {e}")
        
        response = await call_next(request)
        return response


app.add_middleware(AnalyticsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Visitor-Id"],
    expose_headers=["*"],
)


app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(images_router, prefix="/api/v1")
app.include_router(ai_access_router, prefix="/api/v1")
app.include_router(preview_router, prefix="/api/v1")
app.include_router(transcribe_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(audio_router, prefix="/api/v1")


BACKEND_DIR = Path(__file__).resolve().parents[1]

# Generated results: http://localhost:8000/generated/<file>.png
GENERATED_DIR = BACKEND_DIR / "generated_images"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/generated",
    StaticFiles(directory=str(GENERATED_DIR)),
    name="generated",
)

# Reference styles: http://localhost:8000/reference/<prompt_id>/<file>
REFERENCE_DIR = BACKEND_DIR / "reference_images"
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/reference",
    StaticFiles(directory=str(REFERENCE_DIR)),
    name="reference",
)

# Preview samples: http://localhost:8000/preview/<file>.jpg
PREVIEW_DIR = BACKEND_DIR / "preview_images"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/preview",
    StaticFiles(directory=str(PREVIEW_DIR)),
    name="preview",
)


@app.get("/")
def root():
    return {
        "application": "AI Creative Studio",
        "message": "Backend is running",
        "version": "1.0.0",
    }


@app.get("/api/v1/health")
def health():
    return {
        "status": "healthy",
        "backend": "online",
    }

