"""
--- FILE: backend/database/base.py ---

Declarative base for SQLAlchemy models.
"""
from sqlalchemy.orm import declarative_base

# Base declarative class for all ORM models.
Base = declarative_base()

__all__ = ["Base"]
