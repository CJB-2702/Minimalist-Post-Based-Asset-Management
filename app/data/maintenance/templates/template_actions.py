from app.data.maintenance.virtual_action_item import VirtualActionItem
from app import db
from sqlalchemy.orm import relationship

class TemplateActionItem(VirtualActionItem):
    """
    Individual template action items within a template action set
    sequence_order is REQUIRED - defines order within template action set
    """
    __tablename__ = 'template_actions'
    
    # Parent reference - REQUIRED
    template_action_set_id = db.Column(db.Integer, db.ForeignKey('template_action_sets.id'), nullable=False)
    
    # Proto reference
    proto_action_item_id = db.Column(db.Integer, db.ForeignKey('proto_actions.id'), nullable=True)
    
    # Template-specific fields
    is_required = db.Column(db.Boolean, default=True)
    instructions = db.Column(db.Text, nullable=True)
    instructions_type = db.Column(db.String(20), nullable=True)
    minimum_staff_count = db.Column(db.Integer, nullable=False, default=1)
    required_skills = db.Column(db.Text, nullable=True)
    
    # Ordering - REQUIRED
    sequence_order = db.Column(db.Integer, nullable=False)
    
    # Versioning
    revision = db.Column(db.String(20), nullable=True)
    prior_revision_id = db.Column(db.Integer, db.ForeignKey('template_actions.id'), nullable=True)
    
    # Relationships
    template_action_set = relationship('TemplateActionSet', back_populates='template_action_items')
    proto_action_item = relationship('ProtoActionItem', foreign_keys=[proto_action_item_id], back_populates='template_action_items', lazy='select', overlaps='template_action_items')
    
    # Referenced by base actions
    actions = relationship('Action', foreign_keys='Action.template_action_item_id', back_populates='template_action_item', lazy='dynamic', overlaps='template_action_item')
    
    # Child relationships
    template_part_demands = relationship(
        'TemplatePartDemand',
        back_populates='template_action_item',
        lazy='selectin',
        order_by='TemplatePartDemand.sequence_order',
        cascade='all, delete-orphan'
    )
    template_action_tools = relationship(
        'TemplateActionTool',
        back_populates='template_action_item',
        lazy='selectin',
        order_by='TemplateActionTool.sequence_order',
        cascade='all, delete-orphan'
    )
    template_action_attachments = relationship(
        'TemplateActionAttachment',
        back_populates='template_action_item',
        lazy='selectin',
        order_by='TemplateActionAttachment.sequence_order',
        cascade='all, delete-orphan'
    )
    
    # Self-referential relationship for versioning
    prior_revision = relationship('TemplateActionItem', remote_side='TemplateActionItem.id', foreign_keys=[prior_revision_id], backref='subsequent_revisions')
    
    @classmethod
    def get_column_dict(cls) -> set:
        """
        Get set of column names for this model (excluding audit fields and relationship-only fields).
        Returns all columns including template_action_set_id.
        """
        base_fields = VirtualActionItem.get_column_dict()
        template_fields = {
            'template_action_set_id', 'sequence_order', 'is_required', 'instructions', 'instructions_type',
            'minimum_staff_count', 'required_skills', 'proto_action_item_id',
            'revision', 'prior_revision_id'
        }
        return base_fields | template_fields
    
    def __repr__(self):
        return f'<TemplateActionItem {self.id}: {self.action_name} (order: {self.sequence_order})>'
