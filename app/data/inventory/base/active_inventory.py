from pathlib import Path
from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class ActiveInventory(UserCreatedBase):
    """Current inventory levels by part and location"""
    __tablename__ = 'active_inventory'
    
    # Foreign Keys
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=False)
    
    # Quantities
    quantity_on_hand = db.Column(db.Float, default=0.0)
    quantity_allocated = db.Column(db.Float, default=0.0)
    
    # Tracking
    last_movement_date = db.Column(db.DateTime, nullable=True)
    unit_cost_avg = db.Column(db.Float, nullable=True)
    
    # Unique constraint on part and location combination
    __table_args__ = (
        db.UniqueConstraint('part_id', 'major_location_id', name='uix_part_location'),
    )
    
    # Relationships
    part = db.relationship('Part')
    major_location = db.relationship('MajorLocation')
    
    def __repr__(self):
        return f'<ActiveInventory Part:{self.part_id} Location:{self.major_location_id} Qty:{self.quantity_on_hand}>'
    
    # Properties
    @property
    def quantity_available(self):
        """Quantity available (on hand minus allocated)"""
        return self.quantity_on_hand - self.quantity_allocated
    
    @property
    def is_available(self):
        """Check if any quantity available"""
        return self.quantity_available > 0
    
    @property
    def is_low_stock(self):
        """Check if below minimum stock level"""
        if self.part and hasattr(self.part, 'minimum_stock_level'):
            return self.quantity_on_hand <= self.part.minimum_stock_level
        return False
    
    @property
    def total_value(self):
        """Calculate total inventory value"""
        if self.unit_cost_avg:
            return self.quantity_on_hand * self.unit_cost_avg
        return 0
    
    # Methods
    def adjust_quantity(self, amount, movement_type):
        """Adjust inventory quantity"""
        if movement_type in ['Arrival', 'Transfer', 'Return', 'Adjustment']:
            if amount > 0:
                self.quantity_on_hand += amount
            else:
                self.quantity_on_hand = max(0, self.quantity_on_hand + amount)
        elif movement_type in ['Issue']:
            self.quantity_on_hand = max(0, self.quantity_on_hand - abs(amount))
        
        self.last_movement_date = datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'part_id': self.part_id,
            'major_location_id': self.major_location_id,
            'quantity_on_hand': self.quantity_on_hand,
            'quantity_allocated': self.quantity_allocated,
            'quantity_available': self.quantity_available,
            'last_movement_date': self.last_movement_date.isoformat() if self.last_movement_date else None,
            'unit_cost_avg': self.unit_cost_avg,
            'total_value': self.total_value,
            'is_low_stock': self.is_low_stock,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_id': self.created_by_id
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            part_id=data.get('part_id'),
            major_location_id=data.get('major_location_id'),
            quantity_on_hand=data.get('quantity_on_hand', 0.0),
            quantity_allocated=data.get('quantity_allocated', 0.0),
            last_movement_date=data.get('last_movement_date'),
            unit_cost_avg=data.get('unit_cost_avg'),
            created_by_id=data.get('created_by_id')
        )

