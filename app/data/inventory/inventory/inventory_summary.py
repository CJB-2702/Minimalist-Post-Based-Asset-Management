from __future__ import annotations

from app import db
from app.data.core.user_created_base import UserCreatedBase


class InventorySummary(UserCreatedBase):
    """
    Fast lookup summary of inventory by part.

    Goal:
    - Provide a quick lookup of total active inventory quantity by PartDefinition
    - Store rolling average unit cost for common read-heavy screens and reports

    Notes:
    - This is a denormalized table and should be maintained by business-layer inventory operations.
    - Quantity totals are intended to represent the sum of all ActiveInventory rows for the part.
    """

    __tablename__ = "inventory_summary"

    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False, unique=True)

    quantity_on_hand_total = db.Column(db.Float, nullable=False, default=0.0)
    unit_cost_avg = db.Column(db.Float, nullable=True)

    last_updated_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    part = db.relationship("PartDefinition")
    
    def to_dict(self, include_relationships=False, include_audit_fields=True):
        """
        Convert model instance to dictionary
        
        Args:
            include_relationships (bool): Whether to include relationship data
            include_audit_fields (bool): Whether to include audit fields
            
        Returns:
            dict: Dictionary representation of the model
        """
        return super().to_dict(include_relationships=include_relationships, 
                              include_audit_fields=include_audit_fields)
    
    @classmethod
    def from_dict(cls, data_dict, user_id=None, skip_fields=None):
        """
        Create a model instance from a dictionary
        
        Args:
            data_dict (dict): Dictionary containing model data
            user_id (int, optional): User ID for audit fields
            skip_fields (list, optional): Fields to skip during creation
            
        Returns:
            Model instance (not saved to database)
        """
        return super().from_dict(data_dict, user_id=user_id, skip_fields=skip_fields)


