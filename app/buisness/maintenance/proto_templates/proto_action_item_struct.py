"""
Proto Action Item Struct
Data wrapper around ProtoActionItem for convenient access.
Provides cached access and convenience methods - NO business logic.
"""

from typing import List, Optional, Union
from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
from app.data.maintenance.proto_templates.proto_part_demands import ProtoPartDemand
from app.data.maintenance.proto_templates.proto_action_tools import ProtoActionTool
from app.data.maintenance.proto_templates.proto_action_attachments import ProtoActionAttachment


class ProtoActionItemStruct:
    """
    Data wrapper around ProtoActionItem for convenient access.
    Provides cached access and convenience methods - NO business logic.
    
    For business logic: Use ProtoActionContext
    """
    
    def __init__(self, proto_action_item: Union[ProtoActionItem, int]):
        """
        Initialize ProtoActionItemStruct with ProtoActionItem instance or ID.
        
        Args:
            proto_action_item: ProtoActionItem instance or ID
        """
        if isinstance(proto_action_item, int):
            self._proto_action_item = ProtoActionItem.query.get_or_404(proto_action_item)
            self._proto_action_item_id = proto_action_item
        else:
            self._proto_action_item = proto_action_item
            self._proto_action_item_id = proto_action_item.id
        
        # Cache for lazy loading
        self._proto_part_demands = None
        self._proto_action_tools = None
        self._proto_action_attachments = None
    
    @property
    def proto_action_item(self) -> ProtoActionItem:
        """Get the ProtoActionItem instance"""
        return self._proto_action_item
    
    @property
    def proto_action_item_id(self) -> int:
        """Get the proto action item ID"""
        return self._proto_action_item_id
    
    @property
    def id(self) -> int:
        """Get the proto action item ID (alias)"""
        return self._proto_action_item_id
    
    @property
    def proto_part_demands(self) -> List[ProtoPartDemand]:
        """
        Get all proto part demands for this proto action item, ordered by sequence_order.
        
        Returns:
            List of ProtoPartDemand instances
        """
        if self._proto_part_demands is None:
            self._proto_part_demands = sorted(
                self._proto_action_item.proto_part_demands,
                key=lambda ppd: ppd.sequence_order
            )
        return self._proto_part_demands
    
    @property
    def proto_action_tools(self) -> List[ProtoActionTool]:
        """
        Get all proto action tools for this proto action item, ordered by sequence_order.
        
        Returns:
            List of ProtoActionTool instances
        """
        if self._proto_action_tools is None:
            self._proto_action_tools = sorted(
                self._proto_action_item.proto_action_tools,
                key=lambda pat: pat.sequence_order
            )
        return self._proto_action_tools
    
    @property
    def proto_action_attachments(self) -> List[ProtoActionAttachment]:
        """
        Get all proto action attachments for this proto action item, ordered by sequence_order.
        
        Returns:
            List of ProtoActionAttachment instances
        """
        if self._proto_action_attachments is None:
            self._proto_action_attachments = sorted(
                self._proto_action_item.proto_action_attachments,
                key=lambda att: att.sequence_order
            )
        return self._proto_action_attachments
    
    # Convenience properties for common fields
    @property
    def action_name(self) -> str:
        """Get the action name"""
        return self._proto_action_item.action_name
    
    @property
    def description(self) -> Optional[str]:
        """Get the description"""
        return self._proto_action_item.description
    
    @property
    def revision(self) -> Optional[str]:
        """Get the revision"""
        return self._proto_action_item.revision
    
    @property
    def is_required(self) -> bool:
        """Get whether action is required"""
        return self._proto_action_item.is_required
    
    @property
    def prior_revision_id(self) -> Optional[int]:
        """Get the prior revision ID"""
        return self._proto_action_item.prior_revision_id
    
    @property
    def prior_revision(self):
        """Get the prior revision"""
        return self._proto_action_item.prior_revision
    
    @classmethod
    def from_id(cls, proto_action_item_id: int) -> 'ProtoActionItemStruct':
        """
        Create ProtoActionItemStruct from ID.
        
        Args:
            proto_action_item_id: Proto action item ID
            
        Returns:
            ProtoActionItemStruct instance
        """
        return cls(proto_action_item_id)
    
    def refresh(self):
        """Refresh cached data from database"""
        from app import db
        db.session.refresh(self._proto_action_item)
        self._proto_part_demands = None
        self._proto_action_tools = None
        self._proto_action_attachments = None
    
    def __repr__(self):
        revision_str = f' rev={self.revision}' if self.revision else ''
        return f'<ProtoActionItemStruct id={self._proto_action_item_id} action_name="{self.action_name}"{revision_str}>'

