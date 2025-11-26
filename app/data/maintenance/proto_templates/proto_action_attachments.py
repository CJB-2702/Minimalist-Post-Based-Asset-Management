from app.data.core.event_info.attachment import VirtualAttachmentReference
from app import db
from sqlalchemy.orm import relationship

class ProtoActionAttachment(VirtualAttachmentReference):
    """
    Attachments for proto action items
    Generic library attachments for reusable actions
    """
    __tablename__ = 'proto_action_attachments'
    
    # Parent reference - REQUIRED (serves as attached_to_id)
    proto_action_item_id = db.Column(db.Integer, db.ForeignKey('proto_actions.id'), nullable=False)
    
    # Additional fields
    description = db.Column(db.Text, nullable=True)
    sequence_order = db.Column(db.Integer, nullable=False, default=1)
    is_required = db.Column(db.Boolean, default=False)
    
    # Set attached_to_type for parent class
    attached_to_type = db.Column(db.String(20), nullable=False, default='ProtoActionItem')
    
    # Relationships
    proto_action_item = relationship('ProtoActionItem', back_populates='proto_action_attachments')
    attachment = relationship('Attachment', foreign_keys='ProtoActionAttachment.attachment_id', lazy='select')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.attached_to_type:
            self.attached_to_type = 'ProtoActionItem'
    
    def __repr__(self):
        return f'<ProtoActionAttachment {self.id}: {self.attachment_type}>'
