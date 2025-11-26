from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime

# this class is supposed to define information about a part
# ex that a part exists with name washer and serial number 1234567890
# it only has an inventory column for ease of access
# all inventory and issuance information should be managed in the inventory module

class Part(UserCreatedBase):
    __tablename__ = 'parts'
    
    part_number = db.Column(db.String(100), unique=True, nullable=False)
    part_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    manufacturer = db.Column(db.String(200), nullable=True)
    supplier = db.Column(db.String(200), nullable=True)
    unit_cost = db.Column(db.Float, nullable=True)
    current_stock_level = db.Column(db.Float, default=0.0)
    minimum_stock_level = db.Column(db.Float, default=0.0)
    maximum_stock_level = db.Column(db.Float, nullable=True)
    unit_of_measure = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Active')  # Active/Inactive
    
    # Relationships
    part_demands = db.relationship('PartDemand', lazy='dynamic')
    
    def __repr__(self):
        return f'<Part {self.part_number}: {self.part_name}>'
    
    @property
    def is_active(self):
        return self.status == 'Active'
    
    @property
    def is_low_stock(self):
        return self.current_stock_level <= self.minimum_stock_level
    
    @property
    def is_out_of_stock(self):
        return self.current_stock_level <= 0
    
    @property
    def stock_value(self):
        """Calculate total stock value"""
        if self.unit_cost and self.current_stock_level:
            return self.unit_cost * self.current_stock_level
        return 0
    
    def adjust_stock(self, quantity, adjustment_type='add', user_id=None):
        """Adjust stock level"""
        if adjustment_type == 'add':
            self.current_stock_level += quantity
        elif adjustment_type == 'subtract':
            self.current_stock_level = max(0, self.current_stock_level - quantity)
        elif adjustment_type == 'set':
            self.current_stock_level = quantity
        
        if user_id:
            self.updated_by_id = user_id
    
    def get_stock_status(self):
        """Get stock status description"""
        if self.is_out_of_stock:
            return 'Out of Stock'
        elif self.is_low_stock:
            return 'Low Stock'
        else:
            return 'In Stock'
