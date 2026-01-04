from app.data.maintenance.virtual_action_tool import VirtualActionTool
from app import db
from sqlalchemy.orm import relationship

class ProtoActionTool(VirtualActionTool):
    """
    Generic tool requirements that can be referenced by templates
    Optional - templates can copy from proto or define independently
    """
    __tablename__ = 'proto_action_tools'
    
    # Parent reference - REQUIRED
    proto_action_item_id = db.Column(db.Integer, db.ForeignKey('proto_actions.id'), nullable=False)
    
    # Proto-specific fields
    is_required = db.Column(db.Boolean, default=True)
    sequence_order = db.Column(db.Integer, nullable=False, default=1)
    
    # Relationships
    proto_action_item = relationship('ProtoActionItem', back_populates='proto_action_tools')
    tool = relationship('ToolDefinition', foreign_keys='ProtoActionTool.tool_id', lazy='select')
    
    def __repr__(self):
        tool_name = self.tool.tool_name if self.tool else "Unknown"
        req_str = "Required" if self.is_required else "Optional"
        return f'<ProtoActionTool {self.id}: {tool_name} x{self.quantity_required} ({req_str})>'
