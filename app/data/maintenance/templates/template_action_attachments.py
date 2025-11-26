from app.data.core.event_info.attachment import VirtualAttachmentReference
from app import db
from sqlalchemy.orm import relationship

class TemplateActionAttachment(VirtualAttachmentReference):
    """
    Attachments for individual template action items
    Action-specific documentation, diagrams, or instructions
    """
    __tablename__ = 'template_action_attachments'
    
    # Parent reference - REQUIRED (serves as attached_to_id)
    template_action_item_id = db.Column(db.Integer, db.ForeignKey('template_actions.id'), nullable=False)
    
    # Additional fields
    description = db.Column(db.Text, nullable=True)
    sequence_order = db.Column(db.Integer, nullable=False, default=1)
    is_required = db.Column(db.Boolean, default=False)
    
    # Set attached_to_type for parent class
    attached_to_type = db.Column(db.String(20), nullable=False, default='TemplateActionItem')
    
    # Relationships
    template_action_item = relationship('TemplateActionItem', back_populates='template_action_attachments')
    attachment = relationship('Attachment', foreign_keys='TemplateActionAttachment.attachment_id', lazy='select')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.attached_to_type:
            self.attached_to_type = 'TemplateActionItem'
    
    @classmethod
    def get_column_dict(cls) -> set:
        """
        Get set of column names for this model (excluding audit fields and relationship-only fields).
        Returns all columns including template_action_item_id.
        """
        base_fields = VirtualAttachmentReference.get_column_dict()
        template_fields = {
            'template_action_item_id', 'description', 'sequence_order', 'is_required', 'attached_to_type'
        }
        return base_fields | template_fields
    
    def __repr__(self):
        return f'<TemplateActionAttachment {self.id}: {self.attachment_type}>'
