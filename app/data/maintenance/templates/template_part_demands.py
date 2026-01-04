from app.data.maintenance.virtual_part_demand import VirtualPartDemand
from app import db
from sqlalchemy.orm import relationship

class TemplatePartDemand(VirtualPartDemand):
    """
    Parts required for template actions
    Standalone copy - NO proto reference (allows template-specific customization)
    """
    __tablename__ = 'template_part_demands'
    
    # Parent reference - REQUIRED
    template_action_item_id = db.Column(db.Integer, db.ForeignKey('template_actions.id'), nullable=False)
    
    # Template-specific fields
    is_optional = db.Column(db.Boolean, default=False)
    sequence_order = db.Column(db.Integer, nullable=False, default=1)
    
    # Relationships
    template_action_item = relationship('TemplateActionItem', back_populates='template_part_demands')
    part = relationship('PartDefinition', foreign_keys='TemplatePartDemand.part_id', lazy='select')
    
    @property
    def is_required(self):
        return not self.is_optional
    
    @classmethod
    def get_column_dict(cls) -> set:
        """
        Get set of column names for this model (excluding audit fields and relationship-only fields).
        Returns all columns including template_action_item_id.
        """
        base_fields = VirtualPartDemand.get_column_dict()
        template_fields = {
            'template_action_item_id', 'is_optional', 'sequence_order'
        }
        return base_fields | template_fields
    
    def __repr__(self):
        part_name = self.part.part_name if self.part else "Unknown"
        return f'<TemplatePartDemand {self.id}: {part_name} x{self.quantity_required}>'
