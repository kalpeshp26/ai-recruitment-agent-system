"""
--- FILE: backend/services/tts_service.py ---

TTS service that calls Sarvam Bulbul v3 REST API to synthesise speech.
Caller must handle TTSError gracefully; interview flow must continue on failure.
"""
import logging

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

TTS_ENDPOINT = "https://api.sarvam.ai/v1/tts"


class TTSError(Exception):
    """Raised when TTS provider fails to synthesise audio."""


async def synthesise_speech(text: str, voice: str = "default", sample_rate: int = 16000) -> bytes:
    """Call Sarvam Bulbul v3 to produce WAV audio bytes.

    Returns:
        bytes of WAV audio
    Raises:
        TTSError on provider failure
    """
    payload = {"text": text, "voice": voice, "format": "wav", "sample_rate": sample_rate}
    headers = {"Authorization": f"Bearer {settings.SARVAM_TTS_KEY}"} if settings.SARVAM_TTS_KEY else {}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(TTS_ENDPOINT, json=payload, headers=headers)
            r.raise_for_status()
            return r.content
    except httpx.ReadTimeout:
        logger.exception("TTS request timed out")
        raise TTSError("TTS request timed out")
    except Exception:
        logger.exception("TTS provider error")
        raise TTSError("TTS provider failure")
