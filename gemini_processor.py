"""
Gemini API processor for medical audio transcription and documentation generation.
Handles multilingual (Indian languages + English) code-switched hospital conversations.
"""
import os
import time
import uuid
from typing import Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

from models import (
    ProcessingResult, TranscriptSegment, MedicalDocumentation, NurseTask,
    PatientInfo, Symptom, Diagnosis, Medication, VitalSign,
    Priority, TaskStatus, Emotion, InsuranceIssue, NurseHandover, PatientSummary
)

load_dotenv()

# Model to use - gemini-2.0-flash is stable and supports audio
MODEL_NAME = "gemini-2.0-flash"

# Lazy client initialization
_client = None

def get_client():
    """Get or create the Gemini client (lazy initialization)."""
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not configured. "
                "Please add your Gemini API key to the .env file."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def get_medical_prompt() -> str:
    """Generate the comprehensive prompt for medical audio processing."""
    return """
You are an expert medical transcription and documentation AI assistant specialized in Indian healthcare settings.

Process this audio recording from a hospital environment and extract all relevant medical information.

## Context
- This is a recording from an Indian hospital (could be ward rounds, consultations, or nurse handoffs)
- The conversation may be CODE-SWITCHED between Indian languages (Tamil, Hindi, Telugu, Kannada, Malayalam, Bengali) and English medical terminology
- Speakers may include: Doctor, Nurse, Patient, Bystander (patient's family)

## Your Tasks

### 1. TRANSCRIPTION
- Identify each speaker (Doctor, Nurse, Patient, Bystander, or specific names if mentioned)
- Provide accurate timestamps (MM:SS format)
- Transcribe the original content exactly as spoken
- Identify the language of each segment
- Provide English translation for non-English segments
- Detect the speaker's emotion (happy, sad, angry, neutral, concerned, calm)

### 2. MEDICAL DOCUMENTATION
Extract and structure the following:

**Patient Information:**
- Name (if mentioned)
- Age, Gender
- Bed/Room number
- Admission date

**Clinical Information:**
- Chief complaints (main reasons for visit/admission)
- Symptoms (with severity: mild/moderate/severe, and duration)
- Vital signs (BP, Temperature, Pulse, SpO2, etc.)
- Diagnoses (with ICD-10 codes if you can infer them)
- Medications (drug name, dosage, frequency, route, duration)
- Procedures (performed or ordered)
- Instructions (for patient care)
- Follow-up plans

### 3. NURSE TASKS
Extract actionable tasks for nurses with:
- Clear description of what needs to be done
- Priority: HIGH (urgent medications, critical vitals), MEDIUM (routine medications, scheduled procedures), LOW (general monitoring, comfort measures)
- Task type: medication, vitals, procedure, monitoring, other
- Due time (extract from conversation, e.g., "every 6 hours" → due_minutes: 360)
- Patient identifier (name or bed number)
- Medication details if applicable

### 4. STRATEGIC DOCUMENTATION (CRITICAL)

**A. Insurance Audit (Zero-Rejection Policy):**
Act as an Insurance Auditor. Review the extracted clinical info for gaps that could cause claim rejection.
- Rules to check:
    1. If diagnosis is 'Dengue', check for 'Platelet Count' evidence.
    2. If diagnosis is 'Cardiac', check for 'ECG/Echo' evidence.
    3. If admission is >24hrs, require 'Daily Vitals' and 'Doctor Rounds' notes.
    4. If 'Antibiotics' prescribed, require 'Infection Source' or 'WBC Count'.
- For each violation, suggest the specific missing evidence.

**B. Nurse Shift Handover (SBAR):**
Generate a professional SBAR summary for the next shift nurse:
- **Situation**: Current patient state.
- **Background**: Why they are here (brief history).
- **Assessment**: Current diagnosis and vital stability.
- **Recommendation**: Critical tasks for the next 8 hours.

**C. Patient WhatsApp Summary (Care Companion):**
Generate a friendly, simple summary for the patient to be sent via WhatsApp:
- **Language**: Translate to the patient's likely native language (based on audio).
- **Format**:
    - "👋 Hello [Name], here is your care summary from MedDoc Hospital."
    - Bullet points for meds and simple do's/don'ts.
    - "Call us at [Number] for emergency."

## Important Notes
- Be thorough in extracting ALL medications, even if mentioned casually
- Pay attention to time-based instructions ("after 2 hours", "before food", etc.)
- Extract implicit tasks (e.g., "check BP regularly" → create monitoring task)
- If information is unclear or not mentioned, use null/empty values

## Output Format
Return a structured JSON response with:
- summary: Brief 2-3 sentence summary of the conversation
- transcript_segments: Array of transcribed segments
- documentation: Structured medical documentation (including insurance_audit, nurse_handover, patient_summary)
- nurse_tasks: Array of actionable tasks for nurses
"""


def get_response_schema() -> types.Schema:
    """Define the structured output schema for Gemini."""
    return types.Schema(
        type=types.Type.OBJECT,
        properties={
            "summary": types.Schema(
                type=types.Type.STRING,
                description="A concise 2-3 sentence summary of the conversation"
            ),
            "transcript_segments": types.Schema(
                type=types.Type.ARRAY,
                description="List of transcribed segments with speaker and timestamp",
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "speaker": types.Schema(type=types.Type.STRING),
                        "timestamp": types.Schema(type=types.Type.STRING),
                        "content": types.Schema(type=types.Type.STRING),
                        "language": types.Schema(type=types.Type.STRING),
                        "language_code": types.Schema(type=types.Type.STRING),
                        "translation": types.Schema(type=types.Type.STRING, nullable=True),
                        "emotion": types.Schema(
                            type=types.Type.STRING,
                            enum=["happy", "sad", "angry", "neutral", "concerned", "calm"]
                        ),
                    },
                    required=["speaker", "timestamp", "content", "language", "language_code", "emotion"],
                ),
            ),
            "documentation": types.Schema(
                type=types.Type.OBJECT,
                description="Structured medical documentation",
                properties={
                    "patient_info": types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "name": types.Schema(type=types.Type.STRING, nullable=True),
                            "age": types.Schema(type=types.Type.STRING, nullable=True),
                            "gender": types.Schema(type=types.Type.STRING, nullable=True),
                            "bed_number": types.Schema(type=types.Type.STRING, nullable=True),
                            "admission_date": types.Schema(type=types.Type.STRING, nullable=True),
                        }
                    ),
                    "chief_complaints": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING)
                    ),
                    "symptoms": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "name": types.Schema(type=types.Type.STRING),
                                "severity": types.Schema(type=types.Type.STRING, nullable=True),
                                "duration": types.Schema(type=types.Type.STRING, nullable=True),
                                "notes": types.Schema(type=types.Type.STRING, nullable=True),
                            },
                            required=["name"]
                        )
                    ),
                    "vital_signs": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "type": types.Schema(type=types.Type.STRING),
                                "value": types.Schema(type=types.Type.STRING),
                                "time": types.Schema(type=types.Type.STRING, nullable=True),
                                "notes": types.Schema(type=types.Type.STRING, nullable=True),
                            },
                            required=["type", "value"]
                        )
                    ),
                    "diagnoses": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "condition": types.Schema(type=types.Type.STRING),
                                "icd_code": types.Schema(type=types.Type.STRING, nullable=True),
                                "confidence": types.Schema(type=types.Type.STRING, nullable=True),
                                "notes": types.Schema(type=types.Type.STRING, nullable=True),
                            },
                            required=["condition"]
                        )
                    ),
                    "medications": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "drug_name": types.Schema(type=types.Type.STRING),
                                "dosage": types.Schema(type=types.Type.STRING),
                                "frequency": types.Schema(type=types.Type.STRING),
                                "route": types.Schema(type=types.Type.STRING, nullable=True),
                                "duration": types.Schema(type=types.Type.STRING, nullable=True),
                                "instructions": types.Schema(type=types.Type.STRING, nullable=True),
                            },
                            required=["drug_name", "dosage", "frequency"]
                        )
                    ),
                    "procedures": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING)
                    ),
                    "instructions": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING)
                    ),
                    "follow_up": types.Schema(type=types.Type.STRING, nullable=True),
                    "notes": types.Schema(type=types.Type.STRING, nullable=True),
                    "insurance_audit": types.Schema(
                        type=types.Type.ARRAY,
                        description="List of potential insurance claim rejection risks",
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "severity": types.Schema(type=types.Type.STRING, enum=["HIGH", "MEDIUM", "LOW"]),
                                "rule_violated": types.Schema(type=types.Type.STRING),
                                "missing_evidence": types.Schema(type=types.Type.STRING),
                                "suggestion": types.Schema(type=types.Type.STRING),
                            },
                            required=["severity", "rule_violated", "missing_evidence", "suggestion"]
                        )
                    ),
                    "nurse_handover": types.Schema(
                        type=types.Type.OBJECT,
                        description="Structured SBAR summary for shift handover",
                        nullable=True,
                        properties={
                            "summary_sbar": types.Schema(type=types.Type.STRING),
                            "critical_alerts": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                            "pending_actions": types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                        },
                        required=["summary_sbar", "critical_alerts", "pending_actions"]
                    ),
                    "patient_summary": types.Schema(
                        type=types.Type.OBJECT,
                        description="Patient-facing summary for WhatsApp",
                        nullable=True,
                        properties={
                            "translated_content": types.Schema(type=types.Type.STRING),
                            "whatsapp_message": types.Schema(type=types.Type.STRING),
                        },
                        required=["translated_content", "whatsapp_message"]
                    ),
                },
                required=["patient_info", "chief_complaints", "symptoms", "vital_signs", 
                         "diagnoses", "medications", "procedures", "instructions"]
            ),
            "nurse_tasks": types.Schema(
                type=types.Type.ARRAY,
                description="List of actionable tasks for nurses",
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "task_id": types.Schema(type=types.Type.STRING),
                        "description": types.Schema(type=types.Type.STRING),
                        "priority": types.Schema(
                            type=types.Type.STRING,
                            enum=["HIGH", "MEDIUM", "LOW"]
                        ),
                        "task_type": types.Schema(type=types.Type.STRING),
                        "due_time": types.Schema(type=types.Type.STRING, nullable=True),
                        "due_minutes": types.Schema(type=types.Type.INTEGER, nullable=True),
                        "patient_identifier": types.Schema(type=types.Type.STRING, nullable=True),
                        "medication_details": types.Schema(
                            type=types.Type.OBJECT,
                            nullable=True,
                            properties={
                                "drug_name": types.Schema(type=types.Type.STRING),
                                "dosage": types.Schema(type=types.Type.STRING),
                                "frequency": types.Schema(type=types.Type.STRING),
                                "route": types.Schema(type=types.Type.STRING, nullable=True),
                            }
                        ),
                        "status": types.Schema(
                            type=types.Type.STRING,
                            enum=["PENDING", "IN_PROGRESS", "COMPLETED"]
                        ),
                        "notes": types.Schema(type=types.Type.STRING, nullable=True),
                    },
                    required=["task_id", "description", "priority", "task_type", "status"]
                )
            ),
        },
        required=["summary", "transcript_segments", "documentation", "nurse_tasks"]
    )


async def process_youtube_url(url: str) -> ProcessingResult:
    """
    Process a YouTube URL containing hospital audio/video.
    
    Args:
        url: YouTube video URL
        
    Returns:
        ProcessingResult with transcription, documentation, and tasks
    """
    start_time = time.time()
    
    prompt = get_medical_prompt()
    
    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Content(
                parts=[
                    types.Part(
                        file_data=types.FileData(file_uri=url)
                    ),
                    types.Part(text=prompt)
                ]
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=get_response_schema(),
        ),
    )
    
    # Parse the response
    import json
    result_data = json.loads(response.text)
    
    # Convert to Pydantic models
    processing_time = time.time() - start_time
    
    return _parse_response(result_data, processing_time)


async def process_audio_file(file_path: str, mime_type: str = "audio/mp3") -> ProcessingResult:
    """
    Process an uploaded audio file.
    
    Args:
        file_path: Path to the audio file
        mime_type: MIME type of the audio file
        
    Returns:
        ProcessingResult with transcription, documentation, and tasks
    """
    start_time = time.time()
    
    # Upload file to Gemini
    with open(file_path, "rb") as f:
        file_data = f.read()
    
    # Upload the file
    uploaded_file = get_client().files.upload(
        file=file_path,
        config=types.UploadFileConfig(mime_type=mime_type)
    )
    
    # Wait for file to be processed
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(1)
        uploaded_file = get_client().files.get(name=uploaded_file.name)
    
    if uploaded_file.state.name == "FAILED":
        raise Exception(f"File processing failed: {uploaded_file.state.name}")
    
    prompt = get_medical_prompt()
    
    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=[
            types.Content(
                parts=[
                    types.Part(file_data=types.FileData(file_uri=uploaded_file.uri)),
                    types.Part(text=prompt)
                ]
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=get_response_schema(),
        ),
    )
    
    # Clean up uploaded file
    try:
        get_client().files.delete(name=uploaded_file.name)
    except:
        pass  # Ignore cleanup errors
    
    # Parse the response
    import json
    result_data = json.loads(response.text)
    
    processing_time = time.time() - start_time
    
    return _parse_response(result_data, processing_time)


def _parse_response(result_data: dict, processing_time: float) -> ProcessingResult:
    """Parse the JSON response into Pydantic models."""
    
    # Parse transcript segments
    segments = []
    for seg in result_data.get("transcript_segments", []):
        segments.append(TranscriptSegment(
            speaker=seg.get("speaker", "Unknown"),
            timestamp=seg.get("timestamp", "00:00"),
            content=seg.get("content", ""),
            language=seg.get("language", "Unknown"),
            language_code=seg.get("language_code", "un"),
            translation=seg.get("translation"),
            emotion=Emotion(seg.get("emotion", "neutral"))
        ))
    
    # Parse documentation
    doc_data = result_data.get("documentation", {})
    patient_info_data = doc_data.get("patient_info", {})
    
    documentation = MedicalDocumentation(
        patient_info=PatientInfo(
            name=patient_info_data.get("name"),
            age=patient_info_data.get("age"),
            gender=patient_info_data.get("gender"),
            bed_number=patient_info_data.get("bed_number"),
            admission_date=patient_info_data.get("admission_date")
        ),
        chief_complaints=doc_data.get("chief_complaints", []),
        symptoms=[Symptom(**s) for s in doc_data.get("symptoms", [])],
        vital_signs=[VitalSign(**v) for v in doc_data.get("vital_signs", [])],
        diagnoses=[Diagnosis(**d) for d in doc_data.get("diagnoses", [])],
        medications=[Medication(**m) for m in doc_data.get("medications", [])],
        procedures=doc_data.get("procedures", []),
        instructions=doc_data.get("instructions", []),
        follow_up=doc_data.get("follow_up"),
        # New Strategic Fields
        insurance_audit=[InsuranceIssue(**i) for i in doc_data.get("insurance_audit", [])],
        nurse_handover=NurseHandover(**doc_data.get("nurse_handover")) if doc_data.get("nurse_handover") else None,
        patient_summary=PatientSummary(**doc_data.get("patient_summary")) if doc_data.get("patient_summary") else None,
        notes=doc_data.get("notes")
    )
    
    # Parse nurse tasks
    tasks = []
    for task in result_data.get("nurse_tasks", []):
        med_details = task.get("medication_details")
        tasks.append(NurseTask(
            task_id=task.get("task_id", str(uuid.uuid4())[:8]),
            description=task.get("description", ""),
            priority=Priority(task.get("priority", "MEDIUM")),
            task_type=task.get("task_type", "other"),
            due_time=task.get("due_time"),
            due_minutes=task.get("due_minutes"),
            patient_identifier=task.get("patient_identifier"),
            medication_details=Medication(**med_details) if med_details else None,
            status=TaskStatus(task.get("status", "PENDING")),
            notes=task.get("notes")
        ))
    
    return ProcessingResult(
        summary=result_data.get("summary", ""),
        transcript_segments=segments,
        documentation=documentation,
        nurse_tasks=tasks,
        processing_time=processing_time
    )
