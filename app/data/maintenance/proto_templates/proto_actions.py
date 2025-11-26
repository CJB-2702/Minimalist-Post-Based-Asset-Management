from app.data.maintenance.virtual_action_item import VirtualActionItem
from app import db
from sqlalchemy.orm import relationship

class ProtoActionItem(VirtualActionItem):
    """
    Generic, reusable action definition - standalone library item
    NO template_action_set_id - proto items are standalone, not in sets
    NO sequence_order - proto items are library items, not ordered
    """
    __tablename__ = 'proto_actions'
    
    # Proto-specific fields
    is_required = db.Column(db.Boolean, default=True)
    instructions = db.Column(db.Text, nullable=True)
    instructions_type = db.Column(db.String(20), nullable=True)
    minimum_staff_count = db.Column(db.Integer, nullable=False, default=1)
    required_skills = db.Column(db.Text, nullable=True)
    
    # Versioning
    revision = db.Column(db.String(20), nullable=True)
    prior_revision_id = db.Column(db.Integer, db.ForeignKey('proto_actions.id'), nullable=True)
    
    # Relationships
    # Referenced by template action items
    template_action_items = relationship(
        'TemplateActionItem',
        foreign_keys='TemplateActionItem.proto_action_item_id',
        back_populates='proto_action_item',
        lazy='dynamic',
        overlaps='proto_action_item'
    )
    
    # Child relationships (optional - for library)
    proto_part_demands = relationship(
        'ProtoPartDemand',
        back_populates='proto_action_item',
        lazy='selectin',
        order_by='ProtoPartDemand.sequence_order',
        cascade='all, delete-orphan'
    )
    proto_action_tools = relationship(
        'ProtoActionTool',
        back_populates='proto_action_item',
        lazy='selectin',
        order_by='ProtoActionTool.sequence_order',
        cascade='all, delete-orphan'
    )
    proto_action_attachments = relationship(
        'ProtoActionAttachment',
        back_populates='proto_action_item',
        lazy='selectin',
        order_by='ProtoActionAttachment.sequence_order',
        cascade='all, delete-orphan'
    )
    
    # Self-referential relationship for versioning
    prior_revision = relationship('ProtoActionItem', remote_side='ProtoActionItem.id', foreign_keys=[prior_revision_id], backref='subsequent_revisions')
    
    def __repr__(self):
        revision_str = f' (rev {self.revision})' if self.revision else ''
        return f'<ProtoActionItem {self.id}: {self.action_name}{revision_str}>'

