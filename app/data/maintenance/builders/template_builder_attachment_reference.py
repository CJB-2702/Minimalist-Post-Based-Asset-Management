"""
Template Builder Attachment Reference
Data model for tracking newly uploaded attachments during template building.
"""

from app.data.core.user_created_base import UserCreatedBase
from app import db
from sqlalchemy.orm import relationship


class TemplateBuilderAttachmentReference(UserCreatedBase):
    """
    Tracks newly uploaded attachments during template building.
    Only created for new uploads, not for copied attachments from existing templates.
    Marked as finalized upon successful template submission.
    """
    __tablename__ = 'template_builder_attachment_references'
    
    # Builder reference
    template_builder_memory_id = db.Column(
        db.Integer, 
        db.ForeignKey('template_build_memory.id'), 
        nullable=False
    )
    
    # Attachment reference
    attachment_id = db.Column(
        db.Integer, 
        db.ForeignKey('attachments.id'), 
        nullable=False
    )
    
    # Attachment level: 'action_set' or 'action'
    attachment_level = db.Column(db.String(20), nullable=False)
    
    # Action index (if attachment_level is 'action')
    action_index = db.Column(db.Integer, nullable=True)
    
    # Metadata matching TemplateActionSetAttachment/TemplateActionAttachment structure
    description = db.Column(db.Text, nullable=True)
    sequence_order = db.Column(db.Integer, nullable=False, default=1)
    is_required = db.Column(db.Boolean, default=False)
    
    # Status tracking
    is_finalized = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    template_builder_memory = relationship(
        'TemplateBuilderMemory',
        backref='builder_attachment_references'
    )
    attachment = relationship(
        'Attachment',
        foreign_keys=[attachment_id],
        lazy='select'
    )
    
    def __repr__(self):
        level = self.attachment_level
        action_idx = f' action_idx={self.action_index}' if self.action_index is not None else ''
        finalized = ' (finalized)' if self.is_finalized else ''
        return f'<TemplateBuilderAttachmentReference {self.id}: {level}{action_idx}{finalized}>'

