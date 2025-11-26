from app.data.maintenance.virtual_action_set import VirtualActionSet
from app import db
from sqlalchemy.orm import relationship

class TemplateActionSet(VirtualActionSet):
    """
    Template maintenance procedure - container for template actions
    Templates can change over time and need versioning for traceability
    NO sequence_order - standalone templates that can be used in any order
    """
    __tablename__ = 'template_action_sets'
    
    # Template versioning
    revision = db.Column(db.String(20), nullable=True)
    prior_revision_id = db.Column(db.Integer, db.ForeignKey('template_action_sets.id'), nullable=True)
    
    # Template metadata
    is_active = db.Column(db.Boolean, default=True)
    maintenance_plan_id = db.Column(db.Integer, db.ForeignKey('maintenance_plans.id'), nullable=True)
    asset_type_id = db.Column(db.Integer, db.ForeignKey('asset_types.id'), nullable=True)
    make_model_id = db.Column(db.Integer, db.ForeignKey('make_models.id'), nullable=True)
    
    # Relationships
    template_action_items = relationship(
        'TemplateActionItem',
        back_populates='template_action_set',
        lazy='selectin',
        order_by='TemplateActionItem.sequence_order',
        cascade='all, delete-orphan'
    )
    maintenance_plans = relationship(
        'MaintenancePlan',
        back_populates='template_action_set',
        foreign_keys='MaintenancePlan.template_action_set_id',
        lazy='dynamic'
    )
    template_action_set_attachments = relationship(
        'TemplateActionSetAttachment',
        back_populates='template_action_set',
        lazy='selectin',
        order_by='TemplateActionSetAttachment.sequence_order',
        cascade='all, delete-orphan'
    )
    
    # Self-referential relationship for versioning
    prior_revision = relationship('TemplateActionSet', remote_side='TemplateActionSet.id', foreign_keys=[prior_revision_id], backref='subsequent_revisions')
    
    # Referenced by maintenance action sets
    maintenance_action_sets = relationship('MaintenanceActionSet', foreign_keys='MaintenanceActionSet.template_action_set_id', back_populates='template_action_set', lazy='dynamic', overlaps='template_action_set')
    
    @classmethod
    def get_column_dict(cls) -> set:
        """
        Get set of column names for this model (excluding audit fields and relationship-only fields).
        Returns all columns including maintenance_plan_id.
        """
        base_fields = VirtualActionSet.get_column_dict()
        template_fields = {
            'revision', 'prior_revision_id', 'is_active', 
            'maintenance_plan_id', 'asset_type_id', 'make_model_id'
        }
        return base_fields | template_fields
    
    def __repr__(self):
        revision_str = f' (rev {self.revision})' if self.revision else ''
        return f'<TemplateActionSet {self.id}: {self.task_name}{revision_str}>'

