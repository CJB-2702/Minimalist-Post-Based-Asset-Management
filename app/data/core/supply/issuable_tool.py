from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime

#todo this should probably just be an asset with class tool and this as an asset detail.

class IssuableTool(UserCreatedBase):
    """
    Issuable Tool class - represents a tool that can be issued/assigned to users
    This extends the base Tool with issuance-specific functionality
    """
    __tablename__ = 'issuable_tools'
    
    # Foreign key to the base Tool
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), nullable=False)
    
    # Issuance-specific columns (moved from base Tool class)
    serial_number = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Available')  # Available, In Use, Out for Repair, Retired
    last_calibration_date = db.Column(db.Date, nullable=True)
    next_calibration_date = db.Column(db.Date, nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    tool = db.relationship('Tool', backref='issuable_instances')
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], overlaps="assigned_tools")
    
    def __repr__(self):
        return f'<IssuableTool {self.tool.tool_name if self.tool else "Unknown"}: {self.status}>'
    
    @property
    def is_available(self):
        return self.status == 'Available'
    
    @property
    def is_in_use(self):
        return self.status == 'In Use'
    
    @property
    def is_out_for_repair(self):
        return self.status == 'Out for Repair'
    
    @property
    def is_retired(self):
        return self.status == 'Retired'
    
    @property
    def needs_calibration(self):
        """Check if tool needs calibration"""
        if self.next_calibration_date:
            return datetime.utcnow().date() >= self.next_calibration_date
        return False
    
    @property
    def calibration_overdue(self):
        """Check if calibration is overdue"""
        if self.next_calibration_date:
            return datetime.utcnow().date() > self.next_calibration_date
        return False
    
    def assign_to_user(self, user_id):
        """Assign tool to a user"""
        self.assigned_to_id = user_id
        self.status = 'In Use'
    
    def unassign(self):
        """Unassign tool from user"""
        self.assigned_to_id = None
        self.status = 'Available'
    
    def mark_for_repair(self):
        """Mark tool as out for repair"""
        self.status = 'Out for Repair'
        self.assigned_to_id = None
    
    def retire(self):
        """Retire the tool"""
        self.status = 'Retired'
        self.assigned_to_id = None
    
    def update_calibration(self, calibration_date, next_calibration_date=None):
        """Update calibration dates"""
        self.last_calibration_date = calibration_date
        if next_calibration_date:
            self.next_calibration_date = next_calibration_date

