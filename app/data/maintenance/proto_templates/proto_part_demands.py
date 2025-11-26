from app.data.maintenance.virtual_part_demand import VirtualPartDemand
from app import db
from sqlalchemy.orm import relationship

class ProtoPartDemand(VirtualPartDemand):
    """
    Generic part requirements that can be referenced by templates
    Optional - templates can copy from proto or define independently
    """
    __tablename__ = 'proto_part_demands'
    
    # Parent reference - REQUIRED
    proto_action_item_id = db.Column(db.Integer, db.ForeignKey('proto_actions.id'), nullable=False)
    
    # Proto-specific fields
    is_optional = db.Column(db.Boolean, default=False)
    sequence_order = db.Column(db.Integer, nullable=False, default=1)
    
    # Relationships
    proto_action_item = relationship('ProtoActionItem', back_populates='proto_part_demands')
    part = relationship('Part', foreign_keys='ProtoPartDemand.part_id', lazy='select')
    
    @property
    def is_required(self):
        return not self.is_optional
    
    def __repr__(self):
        part_name = self.part.part_name if self.part else "Unknown"
        return f'<ProtoPartDemand {self.id}: {part_name} x{self.quantity_required}>'
