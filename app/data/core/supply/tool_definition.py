from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime

class ToolDefinition(UserCreatedBase):
    __tablename__ = 'tools'
    
    tool_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    tool_type = db.Column(db.String(100), nullable=True)
    manufacturer = db.Column(db.String(200), nullable=True)
    model_number = db.Column(db.String(100), nullable=True)
    
    def __repr__(self):
        return f'<ToolDefinition {self.tool_name}>'
