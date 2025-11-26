#!/usr/bin/env python3
"""
Virtual Sequence Generator Base Class
Provides common functionality for managing database sequences across different modules
"""

from app import db
from sqlalchemy import text
from contextlib import contextmanager
import threading
from abc import ABC, abstractmethod

class VirtualSequenceGenerator(ABC):
    """
    Abstract base class for sequence generators
    Provides common functionality for managing database sequences
    """
    
    _lock = threading.Lock()
    
    @classmethod
    @abstractmethod
    def get_sequence_table_name(cls):
        """
        Abstract method to return the table name for the sequence counter
        Must be implemented by subclasses
        """
        pass
    
    @classmethod
    def get_next_id(cls):
        """
        Get the next available ID from the sequence
        Uses database counter table for thread safety
        """
        with cls._lock:
            # Update counter and get new value atomically
            db.session.execute(text(f"UPDATE {cls.get_sequence_table_name()} SET current_value = current_value + 1"))
            result = db.session.execute(text(f"SELECT current_value FROM {cls.get_sequence_table_name()}"))
            return result.scalar()
    
    @classmethod
    def create_sequence_if_not_exists(cls):
        """
        Create the sequence if it doesn't exist
        For SQLite, we'll use a simple counter table approach
        """
        try:
            # For SQLite, create a simple counter table
            db.session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {cls.get_sequence_table_name()} (
                    id INTEGER PRIMARY KEY,
                    current_value INTEGER DEFAULT 0
                )
            """))
            
            # Initialize the counter if it doesn't exist
            result = db.session.execute(text(f"SELECT COUNT(*) FROM {cls.get_sequence_table_name()}"))
            if result.scalar() == 0:
                db.session.execute(text(f"INSERT INTO {cls.get_sequence_table_name()} (current_value) VALUES (0)"))
            
            db.session.commit()
                
        except Exception as e:
            db.session.rollback()
            raise e
    
    @classmethod
    def reset_sequence(cls, start_value=1):
        """
        Reset the sequence to a specific value
        Useful for testing or data migration
        """
        with cls._lock:
            db.session.execute(text(f"UPDATE {cls.get_sequence_table_name()} SET current_value = {start_value - 1}"))
            db.session.commit()
    
    @classmethod
    def get_current_sequence_value(cls):
        """
        Get the current value of the sequence
        """
        result = db.session.execute(text(f"SELECT current_value FROM {cls.get_sequence_table_name()}"))
        return result.scalar()
    
    @classmethod
    def get_sequence_info(cls):
        """
        Get information about the sequence
        """
        result = db.session.execute(text(f"SELECT current_value FROM {cls.get_sequence_table_name()}"))
        current_value = result.scalar()
        return {
            'table_name': cls.get_sequence_table_name(),
            'current_value': current_value
        }

