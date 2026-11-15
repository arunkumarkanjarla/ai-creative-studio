
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db


app = FastAPI(
    title=settings.APP_NAME,
    description="Open-source AI image, audio and video generation platform",
    version="1.0.0",
)


# React frontend configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.get("/api/v1/health/database")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
            "database_name": "ai-creative-studio",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        ) from exc
