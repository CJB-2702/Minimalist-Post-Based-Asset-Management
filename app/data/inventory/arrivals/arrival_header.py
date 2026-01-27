from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class ArrivalHeader(UserCreatedBase):
    """
    Represents a physical package/shipment arrival.

    Data model only: processing logic belongs in `app/buisness/inventory/...`.
    """
    __tablename__ = 'package_headers'
    
    # Package Identification
    package_number = db.Column(db.String(100), unique=True, nullable=False)
    tracking_number = db.Column(db.String(100), nullable=True)
    carrier = db.Column(db.String(100), nullable=True)
    
    # Receipt Details
    received_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    received_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Location and Status
    major_location_id = db.Column(db.Integer, db.ForeignKey('major_locations.id'), nullable=True)
    storeroom_id = db.Column(db.Integer, db.ForeignKey('storerooms.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Received')  # Received/Inspected/Processed
    
    # Relationships
    part_arrivals = db.relationship('ArrivalLine', back_populates='package_header', lazy='dynamic')
    major_location = db.relationship('MajorLocation')
    storeroom = db.relationship('Storeroom')
    received_by = db.relationship('User', foreign_keys=[received_by_id])
    
    def __repr__(self):
        return f'<ArrivalHeader {self.package_number}>'
    
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

