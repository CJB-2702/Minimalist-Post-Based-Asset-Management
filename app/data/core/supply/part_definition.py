from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime

# this class is supposed to define information about a part
# ex that a part exists with name washer and serial number 1234567890
# all inventory and issuance information should be managed in the inventory module

class PartDefinition(UserCreatedBase):
    __tablename__ = 'parts'
    
    part_number = db.Column(db.String(100), unique=True, nullable=False)
    part_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    manufacturer = db.Column(db.String(200), nullable=True)
    supplier = db.Column(db.String(200), nullable=True)
    revision = db.Column(db.String(50), nullable=True)
    last_unit_cost = db.Column(db.Float, nullable=True)
    unit_of_measure = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Active')  # Active/Inactive
    
    # Relationships
    part_demands = db.relationship('PartDemand', lazy='dynamic')
    
    def __repr__(self):
        return f'<PartDefinition {self.part_number}: {self.part_name}>'
    
    @property
    def is_active(self):
        return self.status == 'Active'
