from app.data.core.user_created_base import UserCreatedBase
from app import db

class MajorLocation(UserCreatedBase):
    __tablename__ = 'major_locations'
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships (no backrefs)
    assets = db.relationship('Asset')
    events = db.relationship('Event', overlaps="major_location")
    
    def __repr__(self):
        return f'<MajorLocation {self.name}>' 