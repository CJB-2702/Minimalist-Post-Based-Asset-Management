"""
Proto Action Context
Business logic context manager for proto action items.
Provides proto action management and statistics.
"""

from typing import List, Optional, Union, Dict, Any
from app import db
from app.buisness.maintenance.proto_templates.proto_action_item_struct import ProtoActionItemStruct
from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem


class ProtoActionContext:
    """
    Business logic context manager for proto action items.
    
    Wraps ProtoActionItemStruct (which wraps ProtoActionItem)
    Provides proto action management and statistics.
    """
    
    def __init__(self, proto_action_item: Union[ProtoActionItem, ProtoActionItemStruct, int]):
        """
        Initialize ProtoActionContext with ProtoActionItem, ProtoActionItemStruct, or ID.
        
        Args:
            proto_action_item: ProtoActionItem instance, ProtoActionItemStruct, or ID
        """
        if isinstance(proto_action_item, ProtoActionItemStruct):
            self._struct = proto_action_item
        elif isinstance(proto_action_item, ProtoActionItem):
            self._struct = ProtoActionItemStruct(proto_action_item)
        else:
            self._struct = ProtoActionItemStruct(proto_action_item)
        
        self._proto_action_item_id = self._struct.proto_action_item_id
    
    @property
    def struct(self) -> ProtoActionItemStruct:
        """Get the underlying ProtoActionItemStruct"""
        return self._struct
    
    @property
    def proto_action_item(self) -> ProtoActionItem:
        """Get the ProtoActionItem instance"""
        return self._struct.proto_action_item
    
    @property
    def proto_action_item_id(self) -> int:
        """Get the proto action item ID"""
        return self._proto_action_item_id
    
    # Statistics
    @property
    def total_part_demands(self) -> int:
        """Get total number of proto part demands"""
        return len(self._struct.proto_part_demands)
    
    @property
    def total_action_tools(self) -> int:
        """Get total number of proto action tools"""
        return len(self._struct.proto_action_tools)
    
    @property
    def total_attachments(self) -> int:
        """Get total number of proto action attachments"""
        return len(self._struct.proto_action_attachments)
    
    @property
    def template_action_items_count(self) -> int:
        """Get count of template action items that reference this proto action item"""
        return self.proto_action_item.template_action_items.count()
    
    # Query methods
    @staticmethod
    def get_all() -> List['ProtoActionContext']:
        """
        Get all proto action items.
        
        Returns:
            List of ProtoActionContext instances
        """
        proto_action_items = ProtoActionItem.query.all()
        return [ProtoActionContext(pai) for pai in proto_action_items]
    
    @staticmethod
    def get_by_action_name(action_name: str) -> List['ProtoActionContext']:
        """
        Get proto action items by action name.
        
        Args:
            action_name: Action name to search for
            
        Returns:
            List of ProtoActionContext instances
        """
        proto_action_items = ProtoActionItem.query.filter_by(action_name=action_name).all()
        return [ProtoActionContext(pai) for pai in proto_action_items]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize proto action item to dictionary.
        
        Returns:
            Dictionary representation of proto action item
        """
        return {
            'id': self._proto_action_item_id,
            'action_name': self._struct.action_name,
            'description': self._struct.description,
            'revision': self._struct.revision,
            'is_required': self._struct.is_required,
            'estimated_duration': self.proto_action_item.estimated_duration,
            'expected_billable_hours': self.proto_action_item.expected_billable_hours,
            'minimum_staff_count': self.proto_action_item.minimum_staff_count,
            'instructions': self.proto_action_item.instructions,
            'instructions_type': self.proto_action_item.instructions_type,
            'required_skills': self.proto_action_item.required_skills,
            'prior_revision_id': self._struct.prior_revision_id,
            'total_part_demands': self.total_part_demands,
            'total_action_tools': self.total_action_tools,
            'total_attachments': self.total_attachments,
            'template_action_items_count': self.template_action_items_count,
        }
    
    def refresh(self):
        """Refresh cached data from database"""
        self._struct.refresh()
    
    def __repr__(self):
        return f'<ProtoActionContext id={self._proto_action_item_id} action_name="{self._struct.action_name}" revision={self._struct.revision}>'

