"""FastAPI dependencies"""
from typing import Generator
from sqlalchemy.orm import Session
from database import get_db as get_db_session, close_db_session
from data_manager import DataManager


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = get_db_session()
    try:
        yield db
    finally:
        close_db_session(db)


def get_data_manager() -> DataManager:
    """Get DataManager instance"""
    return DataManager()
