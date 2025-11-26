from pathlib import Path
from app import db
from app.data.core.user_created_base import UserCreatedBase

class PartDemandPurchaseOrderLine(UserCreatedBase):
    """Association table linking part demands to purchase order lines"""
    __tablename__ = 'part_demand_purchase_order_lines'
    
    # Foreign Keys
    part_demand_id = db.Column(db.Integer, db.ForeignKey('part_demands.id'), nullable=False)
    purchase_order_line_id = db.Column(db.Integer, db.ForeignKey('purchase_order_lines.id'), nullable=False)
    
    # Allocation Details
    quantity_allocated = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    part_demand = db.relationship('PartDemand')
    purchase_order_line = db.relationship('PurchaseOrderLine')
    
    def __repr__(self):
        return f'<PartDemandPOLine Demand:{self.part_demand_id} POLine:{self.purchase_order_line_id} Qty:{self.quantity_allocated}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'part_demand_id': self.part_demand_id,
            'purchase_order_line_id': self.purchase_order_line_id,
            'quantity_allocated': self.quantity_allocated,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_id': self.created_by_id
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            part_demand_id=data.get('part_demand_id'),
            purchase_order_line_id=data.get('purchase_order_line_id'),
            quantity_allocated=data.get('quantity_allocated'),
            notes=data.get('notes'),
            created_by_id=data.get('created_by_id')
        )

