"""
Sarvam AI TTS Service

Converts interview question text to speech using Sarvam Bulbul v3 API.
Integrates Redis caching for efficient repeated audio generation.

Voice: shubh (clear, professional male voice, suitable for formal interviews)
Language: en-IN (Indian English)
"""

import base64
import hashlib
import logging
from typing import Optional

import redis

try:
    from sarvamai import SarvamAI
    from sarvamai.core.api_error import ApiError
    SARVAM_AVAILABLE = True
except ImportError:
    SARVAM_AVAILABLE = False

from config import *

logger = logging.getLogger(__name__)

SARVAM_API_KEY = SARVAM_API_KEY
REDIS_URL = REDIS_URL

# Initialize Redis client
redis_client: Optional[redis.Redis] = None
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=False)
    # Test connection
    redis_client.ping()
    logger.info("Redis cache connected for TTS")
except Exception as e:
    logger.warning(f"Redis TTS cache unavailable: {str(e)}")
    redis_client = None

# Initialize Sarvam client
sarvam_client: Optional['SarvamAI'] = None
if SARVAM_AVAILABLE and SARVAM_API_KEY:
    try:
        sarvam_client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        logger.info("Sarvam AI client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Sarvam client: {str(e)}")
        sarvam_client = None


def _cache_key(text: str) -> str:
    """Generate Redis cache key from text."""
    return f"tts:{hashlib.md5(text.encode()).hexdigest()}"


async def text_to_speech(text: str) -> bytes:
    """
    Convert text to WAV audio bytes using Sarvam Bulbul v3.
    
    Checks Redis cache first for faster repeated playback.
    Caches result for 24 hours (86400 seconds).
    
    Args:
        text: Interview question text (max 2500 chars)
        
    Returns:
        Raw WAV audio bytes (ArrayBuffer for frontend)
        
    Raises:
        Exception: If API key missing, text too long, rate limited, or service unavailable
    """
    
    if not SARVAM_API_KEY:
        raise Exception(
            "Sarvam API key not configured. "
            "Set SARVAM_API_KEY environment variable."
        )
    
    if len(text) > 2500:
        raise Exception("Text too long for TTS (max 2500 characters)")
    
    # Check Redis cache
    cache_key = _cache_key(text)
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(f"TTS cache hit for text: {text[:50]}...")
                return cached
        except Exception as e:
            logger.warning(f"Redis cache get failed: {str(e)}")
    
    # Call Sarvam API using direct HTTP request to bypass buggy SDK parameters
    import requests
    try:
        logger.debug(f"Calling Sarvam TTS (direct POST) for: {text[:50]}...")
        
        url = "https://api.sarvam.ai/text-to-speech"
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": [text],
            "target_language_code": "en-IN",
            "speaker": "shubh",
            "pace": 0.95,
            "speech_sample_rate": 24000,
            "enable_preprocessing": True,
            "model": "bulbul:v3"
        }
        
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        
        if res.status_code == 429:
            raise Exception("TTS rate limit exceeded. Please try again in a few moments.")
        elif res.status_code == 403:
            raise Exception("Invalid Sarvam API key. Check SARVAM_API_KEY in .env")
        elif res.status_code == 422:
            # Text validation error — try truncating
            logger.warning(f"Sarvam returned 422, trying truncated text...")
            truncated = text[:2400]
            payload["inputs"] = [truncated]
            res = requests.post(url, json=payload, headers=headers, timeout=15)
            
        if res.status_code != 200:
            raise Exception(f"Sarvam API error ({res.status_code}): {res.text}")
            
        res_json = res.json()
        audios = res_json.get("audios", [])
        if not audios or len(audios) == 0:
            raise Exception("Sarvam returned empty audio list")
            
        audio_bytes = base64.b64decode(audios[0])
        
        # Cache in Redis for 24 hours
        if redis_client:
            try:
                redis_client.setex(cache_key, 86400, audio_bytes)
                logger.debug("TTS result cached in Redis")
            except Exception as e:
                logger.warning(f"Redis cache set failed: {str(e)}")
                
        return audio_bytes
        
    except Exception as e:
        logger.error(f"Sarvam TTS direct API error: {str(e)}")
        raise Exception(f"TTS service error: {str(e)}")


def get_voice_options() -> dict:
    """
    Get available Sarvam Bulbul v3 voices for interview context.
    
    Returns:
        Dict mapping voice names to descriptions
    """
    return {
        "shubh": "Clear, professional male voice (recommended for formal interviews)",
        "kavya": "Confident and clear female voice",
        "ishita": "Professional female tone",
        "priya": "Natural and warm female voice",
    }

