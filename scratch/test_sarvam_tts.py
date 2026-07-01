import urllib.request
import json
import os
from dotenv import load_dotenv

load_dotenv()

def test_sarvam():
    api_key = os.getenv("SARVAM_API_KEY")
    print(f"Testing Sarvam TTS with API Key: {api_key}")
    
    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "inputs": ["Hello world"],
        "target_language_code": "en-IN",
        "speaker": "shubh",
        "pace": 1.0,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True,
        "model": "bulbul:v3"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as res:
            resp_body = res.read().decode()
            resp_json = json.loads(resp_body)
            print("[SUCCESS] API responded with HTTP 200")
            print("Response Keys:", list(resp_json.keys()))
            if "audios" in resp_json:
                print(f"Generated {len(resp_json['audios'])} audios.")
                print("First audio prefix:", resp_json["audios"][0][:50])
    except Exception as e:
        print("[FAILED] Request failed:", e)
        if hasattr(e, "read"):
            print("Error Details:", e.read().decode())

if __name__ == "__main__":
    test_sarvam()
