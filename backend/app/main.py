
from fastapi import FastAPI

app = FastAPI(
    title="AI Creative Studio API",
    description="Open-source AI image, audio and video generation platform",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {
        "application": "AI Creative Studio",
        "message": "Backend is running",
        "version": "1.0.0",
    }


@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "backend": "online",
    }
