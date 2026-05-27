"""
--- FILE: backend/services/stt_service.py ---

STT service that calls Groq Whisper REST API to transcribe audio bytes.
Raises STTTimeoutError on timeouts (>10s).
"""
import logging
from typing import Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

STT_ENDPOINT = "https://api.groq.com/v1/stt"


class STTTimeoutError(Exception):
    """Raised when STT transcription times out."""


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe WAV audio bytes using Groq Whisper REST endpoint.

    Args:
        audio_bytes: WAV bytes (PCM 16-bit, 16kHz, mono)

    Returns:
        transcript string (may be empty)

    Raises:
        STTTimeoutError on timeout (>10s)
    """
    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"} if settings.GROQ_API_KEY else {}
    try:
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(STT_ENDPOINT, files=files, headers=headers)
            if r.status_code == 504 or r.status_code == 408:
                raise STTTimeoutError("STT provider timed out")
            r.raise_for_status()
            data = r.json()
            transcript = data.get("transcript") or data.get("text") or ""
            return transcript.strip()
    except httpx.ReadTimeout:
        logger.exception("STT read timeout")
        raise STTTimeoutError("STT request timed out")
    except STTTimeoutError:
        raise
    except Exception:
        logger.exception("STT provider error; returning empty transcript")
        return ""
