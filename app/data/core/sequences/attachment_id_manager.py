"""
Attachment ID Manager
Manages all_attachments_id sequence for AttachmentReference tables
"""

from app.data.core.virtual_sequence_generator import VirtualSequenceGenerator


class AttachmentIDManager(VirtualSequenceGenerator):
    """
    Manages all_attachments_id sequence for AttachmentReference tables
    Ensures unique IDs across all attachment reference tables
    """
    
    @classmethod
    def get_sequence_table_name(cls):
        """
        Return the table name for the attachment sequence counter
        """
        return "_sequence_attachment_id"
    
    @classmethod
    def get_next_attachment_id(cls):
        """
        Get the next available attachment ID
        Uses the base class method for thread safety
        """
        return cls.get_next_id()



