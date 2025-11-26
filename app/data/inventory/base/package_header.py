from pathlib import Path
from app import db
from app.data.core.user_created_base import UserCreatedBase
from datetime import datetime

class PackageHeader(UserCreatedBase):
    """Represents a physical package/shipment arrival"""
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
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Received')  # Received/Inspected/Processed
    
    # Relationships
    part_arrivals = db.relationship('PartArrival', back_populates='package_header', lazy='dynamic')
    major_location = db.relationship('MajorLocation')
    received_by = db.relationship('User', foreign_keys=[received_by_id])
    
    def __repr__(self):
        return f'<PackageHeader {self.package_number}>'
    
    # Properties
    @property
    def total_items(self):
        """Count of part arrivals in package"""
        return self.part_arrivals.count()
    
    @property
    def is_processed(self):
        """Check if status is Processed"""
        return self.status == 'Processed'
    
    # Methods
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'package_number': self.package_number,
            'tracking_number': self.tracking_number,
            'carrier': self.carrier,
            'received_date': self.received_date.isoformat() if self.received_date else None,
            'received_by_id': self.received_by_id,
            'major_location_id': self.major_location_id,
            'notes': self.notes,
            'status': self.status,
            'total_items': self.total_items,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by_id': self.created_by_id
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(
            package_number=data.get('package_number'),
            tracking_number=data.get('tracking_number'),
            carrier=data.get('carrier'),
            received_date=data.get('received_date'),
            received_by_id=data.get('received_by_id'),
            major_location_id=data.get('major_location_id'),
            notes=data.get('notes'),
            status=data.get('status', 'Received'),
            created_by_id=data.get('created_by_id')
        )

