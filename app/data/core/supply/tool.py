from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime

class Tool(UserCreatedBase):
    __tablename__ = 'tools'
    
    tool_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    tool_type = db.Column(db.String(100), nullable=True)
    manufacturer = db.Column(db.String(200), nullable=True)
    model_number = db.Column(db.String(100), nullable=True)
    
    # Note: Issuance-specific fields (serial_number, location, status, calibration dates, assigned_to_id)
    # have been moved to the IssuableTool class to separate tool definitions from tool instances
    
    def __repr__(self):
        return f'<Tool {self.tool_name}>'
    
    # Note: Issuance-specific methods (status checks, assignment, calibration, etc.)
    # have been moved to the IssuableTool class to separate tool definitions from tool instances
