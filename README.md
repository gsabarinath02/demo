# 🏥 MedDoc AI - Medical Documentation POC

AI-powered medical documentation system for Indian hospitals. Transcribes multilingual (code-switched) conversations and generates structured medical notes + nurse task reminders.

## Features

- **Multilingual Transcription** - Handles Tamil, Hindi, Telugu + English medical terminology
- **Speaker Diarization** - Identifies Doctor, Nurse, Patient, Bystander
- **Structured Documentation** - Symptoms, diagnoses, medications, vitals, instructions
- **Nurse Tasks** - Priority-based task list with countdown timers
- **Real-time Reminders** - Browser notifications for time-sensitive tasks

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

```bash
# Copy the example env file
copy .env.example .env

# Edit .env and add your Gemini API key
# Get one from: https://aistudio.google.com/apikey
```

### 3. Run the Application

```bash
python -m uvicorn main:app --reload --port 8000
```

### 4. Open in Browser

Navigate to [http://localhost:8000](http://localhost:8000)

## Usage

1. **YouTube URL**: Paste a YouTube URL of a hospital consultation
2. **Upload Audio**: Upload an MP3/WAV/WEBM audio file
3. View the generated:
   - **Transcript** with speaker labels and translations
   - **Medical Documentation** (symptoms, meds, diagnoses)
   - **Nurse Tasks** with countdown timers

## Project Structure

```
├── main.py              # FastAPI application
├── gemini_processor.py  # Gemini API integration
├── models.py            # Pydantic data models
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment file
└── static/
    ├── index.html       # Web interface
    ├── styles.css       # Premium glassmorphism CSS
    └── app.js           # Frontend JavaScript
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/api/health` | GET | Health check |
| `/api/process-url` | POST | Process YouTube URL |
| `/api/process-audio` | POST | Process uploaded audio |
| `/api/tasks/{id}/update` | POST | Update task status |

## Tech Stack

- **Backend**: FastAPI + Google GenAI SDK
- **Frontend**: Vanilla JS with Glassmorphism CSS
- **AI Model**: Gemini 2.0 Flash (audio processing)
