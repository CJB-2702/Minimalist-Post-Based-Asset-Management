from pathlib import Path
from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class InventoryMovement(UserCreatedBase):
    """Audit trail for all inventory changes with complete traceability chain"""
    __tablename__ = 'inventory_movements'
    
    # Core Fields
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=False)
    
    # Movement Details
    movement_type = db.Column(db.String(20), nullable=False)  # Arrival/Issue/Adjustment/Transfer/Return
    quantity = db.Column(db.Float, nullable=False)
    movement_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Reference Fields
    reference_type = db.Column(db.String(50), nullable=True)
    reference_id = db.Column(db.Integer, nullable=True)
    
    # Transfer Fields
    from_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=True)
    to_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=True)
    
    # Cost and Notes
    unit_cost = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Specific References
    part_arrival_id = db.Column(db.Integer, db.ForeignKey('part_arrivals.id'), nullable=True)
    part_demand_id = db.Column(db.Integer, db.ForeignKey('part_demands.id'), nullable=True)
    
    # TRACEABILITY CHAIN FIELDS
    # Links to the original part arrival that introduced this inventory
    initial_arrival_id = db.Column(db.Integer, db.ForeignKey('part_arrivals.id'), nullable=True)
    # Links to the immediately preceding movement in the chain
    previous_movement_id = db.Column(db.Integer, db.ForeignKey('inventory_movements.id'), nullable=True)
    
    # Relationships
    part = db.relationship('Part')
    major_location = db.relationship('MajorLocation', foreign_keys=[major_location_id])
    from_location = db.relationship('MajorLocation', foreign_keys=[from_location_id])
    to_location = db.relationship('MajorLocation', foreign_keys=[to_location_id])
    
    # Direct movement references
    part_arrival = db.relationship('PartArrival', foreign_keys=[part_arrival_id], back_populates='inventory_movements')
    # NOTE: No back_populates for part_demand to avoid circular import
    part_demand = db.relationship('PartDemand')
    
    # Traceability chain relationships
    initial_arrival = db.relationship(
        'PartArrival',
        foreign_keys=[initial_arrival_id],
        back_populates='initial_movements'
    )
    previous_movement = db.relationship(
        'InventoryMovement',
        remote_side='InventoryMovement.id',
        foreign_keys=[previous_movement_id],
        backref='subsequent_movements'
    )
    
    def __repr__(self):
        return f'<InventoryMovement {self.movement_type}: Part {self.part_id}, Qty {self.quantity}>'
    
    # Properties
    @property
    def is_arrival(self):
        """Check if movement type is Arrival"""
        return self.movement_type == 'Arrival'
    
    @property
    def is_issue(self):
        """Check if movement type is Issue"""
        return self.movement_type == 'Issue'
    
    @property
    def is_transfer(self):
        """Check if movement type is Transfer"""
        return self.movement_type == 'Transfer'
    
    @property
    def is_adjustment(self):
        """Check if movement type is Adjustment"""
        return self.movement_type == 'Adjustment'
    
    @property
    def is_return(self):
        """Check if movement type is Return"""
        return self.movement_type == 'Return'
    
    @property
    def total_value(self):
        """Calculate total value of movement"""
        if self.unit_cost:
            return abs(self.quantity) * self.unit_cost
        return 0
    
    # Methods
    def get_movement_chain(self):
        """Get complete chain of movements back to arrival"""
        chain = [self]
        current = self
        
        while current.previous_movement_id:
            current = InventoryMovement.query.get(current.previous_movement_id)
            if current:
                chain.append(current)
            else:
                break
        
        return chain
    
    def get_source_arrival(self):
        """Get original part arrival via initial_arrival_id"""
        if self.initial_arrival_id:
            from app.data.inventory.base.part_arrival import PartArrival
            return PartArrival.query.get(self.initial_arrival_id)
        return None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'part_id': self.part_id,
            'major_location_id': self.major_location_id,
            'movement_type': self.movement_type,
            'quantity': self.quantity,
            'movement_date': self.movement_date.isoformat() if self.movement_date else None,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'from_location_id': self.from_location_id,
            'to_location_id': self.to_location_id,
            'unit_cost': self.unit_cost,
            'notes': self.notes,
            'part_arrival_id': self.part_arrival_id,
            'part_demand_id': self.part_demand_id,
            'initial_arrival_id': self.initial_arrival_id,
            'previous_movement_id': self.previous_movement_id,
            'total_value': self.total_value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_id': self.created_by_id
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            part_id=data.get('part_id'),
            major_location_id=data.get('major_location_id'),
            movement_type=data.get('movement_type'),
            quantity=data.get('quantity'),
            movement_date=data.get('movement_date'),
            reference_type=data.get('reference_type'),
            reference_id=data.get('reference_id'),
            from_location_id=data.get('from_location_id'),
            to_location_id=data.get('to_location_id'),
            unit_cost=data.get('unit_cost'),
            notes=data.get('notes'),
            part_arrival_id=data.get('part_arrival_id'),
            part_demand_id=data.get('part_demand_id'),
            initial_arrival_id=data.get('initial_arrival_id'),
            previous_movement_id=data.get('previous_movement_id'),
            created_by_id=data.get('created_by_id')
        )

