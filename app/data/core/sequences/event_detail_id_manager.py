"""
Event Detail ID Manager
Manages all_event_detail_id sequence for EventDetailVirtual tables
"""

from app.data.core.virtual_sequence_generator import VirtualSequenceGenerator


class EventDetailIDManager(VirtualSequenceGenerator):
    """
    Manages all_event_detail_id sequence for EventDetailVirtual tables
    Ensures unique IDs across all event detail tables
    """
    
    @classmethod
    def get_sequence_table_name(cls):
        """
        Return the table name for the event detail sequence counter
        """
        return "_sequence_event_detail_id"
    
    @classmethod
    def get_next_event_detail_id(cls):
        """
        Get the next available event detail ID
        Uses the base class method for thread safety
        """
        return cls.get_next_id()



