"""
--- FILE: backend/schemas/interview.py ---

Pydantic v2 models for interview API request and response shapes
following docs/INTERVIEW_API_CONTRACTS.md.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class StartInterviewRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=64)
    answer_mode: str = Field(...)
    preferred_language: Optional[str] = None


class StartInterviewResponse(BaseModel):
    session_id: str
    session_token: str
    status: str
    start_time: datetime
    answer_mode: str


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str
    current_question_index: int
    answer_mode: str
    warning_count: int
    time_elapsed_seconds: int


class NextQuestionResponse(BaseModel):
    question_id: str
    question_text: str
    difficulty: str
    category: Optional[str] = None
    time_limit: int
    question_index: int
    tts_audio_url: Optional[str] = None


class SubmitAnswerRequest(BaseModel):
    question_id: str
    answer_text: Optional[str] = None
    answer_audio_url: Optional[str] = None
    response_time_ms: int
    client_request_id: str


class SubmitAnswerResponse(BaseModel):
    answer_id: str
    scores: Dict[str, float]
    ai_feedback: str
    rl: Dict[str, Any]
    next_question_available: bool


class SkipQuestionRequest(BaseModel):
    question_id: str
    client_request_id: str


class SkipQuestionResponse(BaseModel):
    skipped_question_id: str
    penalty: int
    current_question_index: int
    next_question_available: bool


class EndInterviewRequest(BaseModel):
    reason: Optional[str]


class EndInterviewResponse(BaseModel):
    session_id: str
    status: str
    evaluation_id: str
    final_score: float


class InterviewResultResponse(BaseModel):
    session_id: str
    technical_score: float
    communication_score: float
    confidence_score: float
    problem_solving_score: float
    penalty_points: int
    final_score: float
    summary: Optional[str] = None


class ProctoringEventRequest(BaseModel):
    event_type: str
    timestamp: Optional[datetime] = None
    screenshot_url: Optional[str] = None


class ProctoringEventResponse(BaseModel):
    violation_id: str
    warning_number: int
    session_status: str


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"
    format: Optional[str] = "wav"
    sample_rate: Optional[int] = 16000


class TTSResponse(BaseModel):
    audio_url: str
    duration_ms: int


class STTRequest(BaseModel):
    audio_url: str
    format: str = "wav"
    timeout_seconds: int = 10


class STTResponse(BaseModel):
    transcript: str
    confidence: float
    duration_ms: int
