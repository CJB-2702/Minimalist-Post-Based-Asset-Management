from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class PartIssue(UserCreatedBase):
    """
    Tracks parts issued to users and part demands.
    Links to InventoryMovement for quantity tracking.
    
    Supports:
    - Direct user issuance
    - Part demand fulfillment
    """
    __tablename__ = 'part_issues'
    
    # Core Links
    inventory_movement_id = db.Column(
        db.Integer, 
        db.ForeignKey('inventory_movements.id'), 
        nullable=False, 
        unique=True
    )  # One-to-one with InventoryMovement
    
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    quantity_issued = db.Column(db.Float, nullable=False)
    unit_cost_at_issue = db.Column(db.Float, nullable=True)
    total_cost = db.Column(db.Float, nullable=True)  # quantity_issued * unit_cost_at_issue
    
    # Issue Recipient (ALWAYS one of these must be set)
    issued_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    part_demand_id = db.Column(db.Integer, db.ForeignKey('part_demands.id'), nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    
    # Issue Details
    issue_type = db.Column(db.String(30), nullable=False)  
    # Values: 'DirectToUser', 'ForPartDemand'
    issue_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Location Info (denormalized from InventoryMovement for query efficiency)
    issued_from_storeroom_id = db.Column(db.Integer, db.ForeignKey('storerooms.id'), nullable=True)
    issued_from_location_id = db.Column(db.Integer, nullable=True)
    issued_from_bin_id = db.Column(db.Integer, nullable=True)
    
    # Business Context
    issue_reason = db.Column(db.String(100), nullable=True)  # leave unused for now
    
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    issued_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Notes
    issue_notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    inventory_movement = db.relationship(
        'InventoryMovement', 
        foreign_keys=[inventory_movement_id]
        # Note: InventoryMovement also has part_issue_id FK for reverse lookup
    )
    
    # Constraints
    __table_args__ = (
        # At least one of user_id, asset_id, or part_demand_id is required
        db.CheckConstraint(
            'issued_to_user_id IS NOT NULL OR asset_id IS NOT NULL OR part_demand_id IS NOT NULL',
            name='check_issue_recipient'
        ),
        # If part_demand_id is set, then asset_id is required
        db.CheckConstraint(
            '(part_demand_id IS NULL) OR (part_demand_id IS NOT NULL AND asset_id IS NOT NULL)',
            name='check_part_demand_requires_asset'
        )
    )
    
    def __repr__(self):
        recipient = f"User {self.issued_to_user_id}" if self.issued_to_user_id else f"Demand {self.part_demand_id}"
        return f'<PartIssue {self.id}: Part {self.part_id} x{self.quantity_issued} to {recipient}>'

