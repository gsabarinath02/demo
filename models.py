"""
Pydantic models for structured medical documentation output.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class Emotion(str, Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    NEUTRAL = "neutral"
    CONCERNED = "concerned"
    CALM = "calm"


# === Transcription Models ===

class TranscriptSegment(BaseModel):
    """A single segment of transcribed speech."""
    speaker: str = Field(description="Speaker identifier (Doctor, Nurse, Patient, Bystander)")
    timestamp: str = Field(description="Timestamp in MM:SS format")
    content: str = Field(description="Original transcribed content")
    language: str = Field(description="Primary language of the segment")
    language_code: str = Field(description="ISO language code (e.g., 'ta', 'hi', 'en')")
    translation: Optional[str] = Field(default=None, description="English translation if not in English")
    emotion: Emotion = Field(description="Detected emotion of the speaker")


# === Medical Documentation Models ===

class Symptom(BaseModel):
    """A symptom reported or observed."""
    name: str = Field(description="Name of the symptom")
    severity: Optional[str] = Field(default=None, description="Severity: mild, moderate, severe")
    duration: Optional[str] = Field(default=None, description="How long the symptom has been present")
    notes: Optional[str] = Field(default=None, description="Additional notes about the symptom")


class Diagnosis(BaseModel):
    """A diagnosis made by the doctor."""
    condition: str = Field(description="Name of the diagnosed condition")
    icd_code: Optional[str] = Field(default=None, description="ICD-10 code if applicable")
    confidence: Optional[str] = Field(default=None, description="Confidence level: confirmed, suspected, ruled_out")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class Medication(BaseModel):
    """A medication prescribed or administered."""
    drug_name: str = Field(description="Name of the medication")
    dosage: str = Field(description="Dosage amount (e.g., '500mg')")
    frequency: str = Field(description="How often to take (e.g., 'twice daily', 'every 6 hours')")
    route: Optional[str] = Field(default="oral", description="Route of administration (oral, IV, IM, etc.)")
    duration: Optional[str] = Field(default=None, description="Duration of treatment")
    instructions: Optional[str] = Field(default=None, description="Special instructions")


class VitalSign(BaseModel):
    """A vital sign measurement."""
    type: str = Field(description="Type of vital (BP, Temperature, Pulse, SpO2, etc.)")
    value: str = Field(description="Measured value with units")
    time: Optional[str] = Field(default=None, description="Time of measurement")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class PatientInfo(BaseModel):
    """Basic patient information extracted from conversation."""
    name: Optional[str] = Field(default=None, description="Patient name if mentioned")
    age: Optional[str] = Field(default=None, description="Patient age")
    gender: Optional[str] = Field(default=None, description="Patient gender")
    bed_number: Optional[str] = Field(default=None, description="Bed/room number if mentioned")
    admission_date: Optional[str] = Field(default=None, description="Admission date if mentioned")


class InsuranceIssue(BaseModel):
    """Potential insurance claim rejection risk."""
    severity: str = Field(description="Severity of the issue: HIGH, MEDIUM, LOW")
    rule_violated: str = Field(description="The insurance rule that was violated")
    missing_evidence: str = Field(description="What evidence/documentation is missing")
    suggestion: str = Field(description="Actionable suggestion for the doctor")


class NurseHandover(BaseModel):
    """Structured SBAR summary for shift handover."""
    summary_sbar: str = Field(description="SBAR format summary for shift handover")
    critical_alerts: List[str] = Field(description="List of critical, high-priority alerts for the next nurse")
    pending_actions: List[str] = Field(description="Actions that must be completed in the next shift")


class PatientSummary(BaseModel):
    """Patient-facing summary for communication."""
    translated_content: str = Field(description="Patient-friendly summary translated to the patient's likely native language")
    whatsapp_message: str = Field(description="Formatted text suitable for a WhatsApp message")


class MedicalDocumentation(BaseModel):
    """Complete structured medical documentation."""
    patient_info: PatientInfo = Field(description="Patient demographic information")
    chief_complaints: List[str] = Field(default_factory=list, description="Primary reasons for visit")
    symptoms: List[Symptom] = Field(default_factory=list, description="Reported/observed symptoms")
    vital_signs: List[VitalSign] = Field(default_factory=list, description="Vital sign measurements")
    diagnoses: List[Diagnosis] = Field(default_factory=list, description="Diagnoses made")
    medications: List[Medication] = Field(default_factory=list, description="Medications prescribed/administered")
    procedures: List[str] = Field(default_factory=list, description="Procedures performed or ordered")
    instructions: List[str] = Field(default_factory=list, description="Patient care instructions")
    follow_up: Optional[str] = Field(default=None, description="Follow-up instructions")
    insurance_audit: List[InsuranceIssue] = Field(default_factory=list, description="List of potential insurance claim rejection risks")
    nurse_handover: Optional[NurseHandover] = Field(default=None, description="Structured shift handover information")
    patient_summary: Optional[PatientSummary] = Field(default=None, description="Patient-facing summary for WhatsApp")
    notes: Optional[str] = Field(default=None, description="Additional clinical notes")


# === Nurse Task Models ===

class NurseTask(BaseModel):
    """A task for nurses extracted from the conversation."""
    task_id: str = Field(description="Unique task identifier")
    description: str = Field(description="Description of the task")
    priority: Priority = Field(description="Task priority")
    task_type: str = Field(description="Type of task: medication, vitals, procedure, monitoring, other")
    due_time: Optional[str] = Field(default=None, description="When the task is due (relative time like 'in 2 hours' or specific time)")
    due_minutes: Optional[int] = Field(default=None, description="Minutes from now when task is due")
    patient_identifier: Optional[str] = Field(default=None, description="Patient name or bed number")
    medication_details: Optional[Medication] = Field(default=None, description="Medication details if applicable")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    notes: Optional[str] = Field(default=None, description="Additional notes for the task")


# === Complete Response Model ===

class ProcessingResult(BaseModel):
    """Complete result from processing hospital audio."""
    summary: str = Field(description="Brief summary of the conversation")
    transcript_segments: List[TranscriptSegment] = Field(description="Transcribed conversation segments")
    documentation: MedicalDocumentation = Field(description="Structured medical documentation")
    nurse_tasks: List[NurseTask] = Field(description="Tasks extracted for nurses")
    processing_time: Optional[float] = Field(default=None, description="Time taken to process in seconds")
