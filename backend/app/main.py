
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.images import router as images_router
from app.api.v1.ai_access import router as ai_access_router
from app.api.v1.preview import router as preview_router


# Do NOT load AI models here.
# Image model loads lazily on the first /images/generate request.
app = FastAPI(
    title="AI Creative Studio API",
    description="Open-source AI image, audio and video generation platform",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["*"],
)


app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(images_router, prefix="/api/v1")
app.include_router(ai_access_router, prefix="/api/v1")
app.include_router(preview_router, prefix="/api/v1")


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

