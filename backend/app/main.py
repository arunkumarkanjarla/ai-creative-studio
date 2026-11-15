
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router


app = FastAPI(
    title="AI Creative Studio API",
    description="Open-source AI image, audio and video generation platform",
    version="1.0.0"
)


# React development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"]
)


app.include_router(
    auth_router,
    prefix="/api/v1"
)

app.include_router(
    users_router,
    prefix="/api/v1"
)


@app.get("/")
def root():

    return {
        "application": "AI Creative Studio",
        "message": "Backend is running",
        "version": "1.0.0"
    }


@app.get("/api/v1/health")
def health():

    return {
        "status": "healthy",
        "backend": "online"
    }
