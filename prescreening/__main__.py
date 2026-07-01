"""
prescreening/__main__.py — Start the prescreening chatbot
"""
import sys
import uvicorn

def main():
    uvicorn.run(
        "prescreening.screening_chatbot:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )

if __name__ == "__main__":
    main()
