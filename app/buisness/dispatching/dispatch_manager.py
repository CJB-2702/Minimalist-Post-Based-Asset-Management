"""
DispatchManager - Simple CRUD helpers for dispatch operations

Provides lightweight helper methods for creating requests.
Business logic is handled by DispatchContext.
"""

from app import db
from app.data.dispatching.request import DispatchRequest


class DispatchManager:
    """
    Simple manager with CRUD helpers.
    Use DispatchContext for business logic operations.
    """
    
    @staticmethod
    def create_request(**kwargs):
        """
        Create a dispatch request (event will be auto-created by EventDetailVirtual)
        
        Args:
            **kwargs: Fields for DispatchRequest creation
            
        Returns:
            DispatchRequest: The created request
        """
        request = DispatchRequest(**kwargs)
        db.session.add(request)
        db.session.flush()  # Get ID and trigger event creation
        
        # Ensure event is created (EventDetailVirtual should handle this)
        if not request.event_id:
            request.create_event()
            db.session.flush()
        
        return request

