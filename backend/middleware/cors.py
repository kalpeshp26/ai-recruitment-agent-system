"""
--- FILE: backend/middleware/cors.py ---

CORS middleware application helper.
"""
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings


def add_cors(app):
    """Attach CORS middleware to the FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
