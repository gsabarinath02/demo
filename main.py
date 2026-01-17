"""
FastAPI application for Medical Documentation POC.
Processes hospital audio and generates structured documentation + nurse tasks.
"""
import os
import uuid
import tempfile
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from gemini_processor import process_youtube_url, process_audio_file
from models import ProcessingResult

load_dotenv()

# Ensure static directory exists
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Temp directory for uploaded files
TEMP_DIR = Path(tempfile.gettempdir()) / "medical_doc_poc"
TEMP_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("[*] Medical Documentation POC starting...")
    print(f"[*] Static files: {STATIC_DIR}")
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("[!] WARNING: GOOGLE_API_KEY not set. Add it to .env file.")
    else:
        print("[+] Gemini API key configured")
    
    yield
    
    # Shutdown
    print("[*] Shutting down...")


app = FastAPI(
    title="Medical Documentation POC",
    description="AI-powered medical transcription and documentation system for Indian hospitals",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Request/Response Models ===

class URLRequest(BaseModel):
    """Request model for YouTube URL processing."""
    url: str


class TaskUpdateRequest(BaseModel):
    """Request model for updating task status."""
    task_id: str
    status: str  # PENDING, IN_PROGRESS, COMPLETED


# === API Endpoints ===

@app.get("/")
async def root():
    """Serve the main HTML page."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Medical Documentation POC API", "docs": "/docs"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    has_api_key = bool(os.getenv("GOOGLE_API_KEY"))
    return {
        "status": "healthy",
        "api_key_configured": has_api_key
    }


@app.post("/api/process-url")
async def process_url(request: URLRequest) -> dict:
    """
    Process a YouTube URL containing hospital audio/video.
    
    - Transcribes the audio with speaker diarization
    - Extracts medical documentation
    - Generates nurse tasks with reminders
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY not configured. Add it to .env file."
        )
    
    try:
        result = await process_youtube_url(request.url)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process-audio")
async def process_audio(
    file: UploadFile = File(...),
) -> dict:
    """
    Process an uploaded audio file.
    
    Supported formats: MP3, WAV, WEBM, OGG, M4A
    """
    if not os.getenv("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY not configured. Add it to .env file."
        )
    
    # Validate file type
    allowed_types = {
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mp4": "m4a",
        "audio/x-m4a": "m4a",
        "video/webm": "webm",  # Browser may send video/webm for audio recordings
    }
    
    content_type = file.content_type or "audio/mpeg"
    if content_type not in allowed_types:
        # Try to infer from filename
        ext = Path(file.filename or "").suffix.lower().lstrip(".")
        if ext not in ["mp3", "wav", "webm", "ogg", "m4a"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format: {content_type}. Use MP3, WAV, WEBM, OGG, or M4A."
            )
    
    try:
        # Save uploaded file temporarily
        file_ext = allowed_types.get(content_type, "mp3")
        temp_path = TEMP_DIR / f"{uuid.uuid4()}.{file_ext}"
        
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process the audio
        result = await process_audio_file(str(temp_path), content_type)
        
        # Clean up
        try:
            temp_path.unlink()
        except:
            pass
        
        return result.model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/update")
async def update_task(task_id: str, request: TaskUpdateRequest):
    """
    Update the status of a nurse task.
    
    Note: In a production system, this would update a database.
    For this POC, we just acknowledge the update.
    """
    return {
        "success": True,
        "task_id": task_id,
        "new_status": request.status
    }


# Mount static files (after API routes)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
