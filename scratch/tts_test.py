import asyncio
import sys
import os
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from services.sarvam_service import text_to_speech

async def test():
    try:
        audio = await text_to_speech("Hello, welcome to your AI interview. Lets begin.")
        print(f"[SUCCESS] Got {len(audio)} bytes of WAV audio")
    except Exception as e:
        print(f"[FAILED] {e}")

asyncio.run(test())
