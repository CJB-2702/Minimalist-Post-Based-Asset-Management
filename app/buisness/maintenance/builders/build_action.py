"""
Build Action Wrapper
Lightweight wrapper around action dict data with methods to manage tools and part demands.
"""

from typing import Dict, Any, Optional, List
from app.data.maintenance.templates.template_actions import TemplateActionItem
from app.data.maintenance.templates.template_part_demands import TemplatePartDemand
from app.data.maintenance.templates.template_action_tools import TemplateActionTool
from app.data.maintenance.templates.template_action_attachments import TemplateActionAttachment
from app.data.maintenance.proto_templates.proto_actions import ProtoActionItem
from app.buisness.maintenance.builders.build_part_demand import BuildPartDemand
from app.buisness.maintenance.builders.build_action_tool import BuildActionTool
from app.buisness.maintenance.builders.build_attachment import BuildAttachment

#in get_valid_fields, we need to include the part_demands, tools, and attachments fields 
# because they are not in the TemplateActionItem model, but they are in the BuildAction model.

class BuildAction:
    """
    Wrapper for action data in template builder.
    Wraps a dict internally, contains lists of BuildPartDemand and BuildActionTool,
    and provides methods to manage them.
    """
    
    # Valid fields from VirtualActionItem and TemplateActionItem
    _valid_fields = None
    
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        """
        Initialize BuildAction with data dict.
        
        Args:
            data: Dictionary containing action fields. If None, creates empty dict.
        """
        if data is None:
            data = {}
        self._data = dict(data)
        self._ensure_valid_fields()
        
        # Initialize part demands, tools, and attachments from data
        self._part_demands: List[BuildPartDemand] = []
        self._tools: List[BuildActionTool] = []
        self._attachments: List[BuildAttachment] = []
        
        # Load part demands from data
        if 'part_demands' in self._data:
            for pd_data in self._data['part_demands']:
                self._part_demands.append(BuildPartDemand(pd_data))
            # Remove from _data to avoid duplication
            del self._data['part_demands']
        
        # Load tools from data
        if 'tools' in self._data:
            for tool_data in self._data['tools']:
                self._tools.append(BuildActionTool(tool_data))
            # Remove from _data to avoid duplication
            del self._data['tools']
        
        # Load attachments from data
        if 'attachments' in self._data:
            for att_data in self._data['attachments']:
                self._attachments.append(BuildAttachment(att_data))
            # Remove from _data to avoid duplication
            del self._data['attachments']
    
    @classmethod
    def _get_valid_fields(cls) -> set: #!!!!!!!!!!!!!!! IMPORTANT !!!!!!!!!!!!!!!!
        """Get valid field names from TemplateActionItem model, excluding builder-invalid fields."""
        # We need to include the part_demands, tools, and attachments fields 
        # because they are not in the TemplateActionItem model, but they are in the BuildAction model.
        if cls._valid_fields is None:
            template_action_item_fields = TemplateActionItem.get_column_dict()
            all_fields = template_action_item_fields | {"part_demands", "tools", "attachments"}
            invalid_columns = ['template_action_set_id']
            cls._valid_fields = all_fields - set(invalid_columns)
        return cls._valid_fields
    
    def _ensure_valid_fields(self):
        """Remove any invalid fields from _data."""
        valid_fields = self._get_valid_fields() 
        self._data = {k: v for k, v in self._data.items() if k in valid_fields}
    
    # Getters for common fields
    @property
    def action_name(self) -> Optional[str]:
        """Get action_name."""
        return self._data.get('action_name')
    
    @action_name.setter
    def action_name(self, value: Optional[str]):
        """Set action_name."""
        if value:
            self._data['action_name'] = str(value)
        elif 'action_name' in self._data:
            del self._data['action_name']
    
    @property
    def description(self) -> Optional[str]:
        """Get description."""
        return self._data.get('description')
    
    @description.setter
    def description(self, value: Optional[str]):
        """Set description."""
        if value:
            self._data['description'] = str(value)
        elif 'description' in self._data:
            del self._data['description']
    
    @property
    def sequence_order(self) -> Optional[int]:
        """Get sequence_order."""
        return self._data.get('sequence_order')
    
    @sequence_order.setter
    def sequence_order(self, value: Optional[int]):
        """Set sequence_order."""
        if value is not None:
            self._data['sequence_order'] = int(value)
        elif 'sequence_order' in self._data:
            del self._data['sequence_order']
    
    @property
    def proto_action_item_id(self) -> Optional[int]:
        """Get proto_action_item_id."""
        return self._data.get('proto_action_item_id')
    
    @proto_action_item_id.setter
    def proto_action_item_id(self, value: Optional[int]):
        """Set proto_action_item_id."""
        if value is not None:
            self._data['proto_action_item_id'] = int(value)
        elif 'proto_action_item_id' in self._data:
            del self._data['proto_action_item_id']
    
    @property
    def estimated_duration(self) -> Optional[float]:
        """Get estimated_duration."""
        return self._data.get('estimated_duration')
    
    @estimated_duration.setter
    def estimated_duration(self, value: Optional[float]):
        """Set estimated_duration."""
        if value is not None:
            self._data['estimated_duration'] = float(value)
        elif 'estimated_duration' in self._data:
            del self._data['estimated_duration']
    
    @property
    def part_demands(self) -> List[BuildPartDemand]:
        """Get list of part demands."""
        return self._part_demands
    
    @property
    def tools(self) -> List[BuildActionTool]:
        """Get list of tools."""
        return self._tools
    
    @property
    def attachments(self) -> List[BuildAttachment]:
        """Get list of attachments."""
        return self._attachments
    
    # Methods to manage part demands
    def add_part_demand(self, part_data: Dict[str, Any]) -> BuildPartDemand:
        """
        Add a part demand to this action.
        
        Args:
            part_data: Dictionary containing part demand fields
            
        Returns:
            BuildPartDemand: The created part demand wrapper
        """

        part_demand = BuildPartDemand.from_dict(data=part_data)
        self._part_demands.append(part_demand)
        return part_demand
    
    def remove_part_demand(self, index: int):
        """
        Remove a part demand by index.
        
        Args:
            index: Index of part demand to remove
        """
        if 0 <= index < len(self._part_demands):
            self._part_demands.pop(index)
    
    # Methods to manage tools
    def add_tool(self, tool_data: Dict[str, Any]) -> BuildActionTool:
        """
        Add a tool to this action.
        
        Args:
            tool_data: Dictionary containing tool fields
            
        Returns:
            BuildActionTool: The created tool wrapper
        """
        tool = BuildActionTool(tool_data)
        self._tools.append(tool)
        return tool
    
    def remove_tool(self, index: int):
        """
        Remove a tool by index.
        
        Args:
            index: Index of tool to remove
        """
        if 0 <= index < len(self._tools):
            self._tools.pop(index)
    
    # Methods to manage attachments
    def add_attachment(self, attachment_data: Dict[str, Any]) -> BuildAttachment:
        """
        Add an attachment to this action.
        
        Args:
            attachment_data: Dictionary containing attachment reference fields
            
        Returns:
            BuildAttachment: The created attachment wrapper
        """
        attachment = BuildAttachment(attachment_data)
        self._attachments.append(attachment)
        return attachment
    
    def remove_attachment(self, index: int):
        """
        Remove an attachment by index.
        
        Args:
            index: Index of attachment to remove
        """
        if 0 <= index < len(self._attachments):
            self._attachments.pop(index)
    
    # Methods to manage proto action reference
    def link_to_proto_action(self, proto_action_item_id: int):
        """
        Link this action to a proto action.
        
        Args:
            proto_action_item_id: ID of the proto action item
        """
        self.proto_action_item_id = proto_action_item_id
    
    def unlink_proto_action(self):
        """Unlink proto action reference (keeps all copied data)."""
        self.proto_action_item_id = None
    
    # Class methods for creating from different sources
    @classmethod
    def from_template_item(cls, template_action_item_id: int, sequence_order: Optional[int] = None) -> 'BuildAction':
        """
        Create a BuildAction by copying from an existing TemplateActionItem.
        
        Args:
            template_action_item_id: ID of template action item to copy
            sequence_order: Optional sequence order to override template's sequence_order
            
        Returns:
            BuildAction: The created action wrapper with all part demands and tools copied
        """
        template_action = TemplateActionItem.query.get_or_404(template_action_item_id)
        
        # Create action data dict using BuildAction's valid fields (invalid columns already filtered)
        action_data = {}
        valid_fields = cls._get_valid_fields()
        for key in valid_fields:
            if hasattr(template_action, key):
                value = getattr(template_action, key)
                if value is not None:
                    action_data[key] = value
        
        # Override sequence_order if provided
        if sequence_order is not None:
            action_data['sequence_order'] = sequence_order
        
        # Create BuildAction
        action = cls(action_data)
        
        # Copy part demands using BuildPartDemand's valid fields (invalid columns already filtered)
        for template_part_demand in template_action.template_part_demands:
            part_data = {}
            valid_part_fields = BuildPartDemand._get_valid_fields()
            for key in valid_part_fields:
                if hasattr(template_part_demand, key):
                    value = getattr(template_part_demand, key)
                    if value is not None:
                        part_data[key] = value
            action.add_part_demand(part_data)
        
        # Copy tools using BuildActionTool's valid fields (invalid columns already filtered)
        for template_tool in template_action.template_action_tools:
            tool_data = {}
            valid_tool_fields = BuildActionTool._get_valid_fields()
            for key in valid_tool_fields:
                if hasattr(template_tool, key):
                    value = getattr(template_tool, key)
                    if value is not None:
                        tool_data[key] = value
            action.add_tool(tool_data)
        
        # Copy attachments using BuildAttachment's valid fields (invalid columns already filtered)
        for template_attachment in template_action.template_action_attachments:
            attachment_data = {}
            valid_att_fields = BuildAttachment._get_valid_fields()
            for key in valid_att_fields:
                if hasattr(template_attachment, key):
                    value = getattr(template_attachment, key)
                    if value is not None:
                        attachment_data[key] = value
            action.add_attachment(attachment_data)
        
        return action
    
    @classmethod
    def from_proto(cls, proto_action_id: int, sequence_order: Optional[int] = None) -> 'BuildAction':
        """
        Create a BuildAction by copying from a ProtoActionItem.
        
        Args:
            proto_action_id: ID of proto action item to copy
            sequence_order: Optional sequence order (required if not provided)
            
        Returns:
            BuildAction: The created action wrapper with all part demands and tools copied
        """
        proto_action = ProtoActionItem.query.get_or_404(proto_action_id)
        
        # Create action data dict using TemplateActionItem.get_column_dict() for field validation
        # Proto actions may not have all template fields, so we map what's available
        action_data = {}
        valid_fields = TemplateActionItem.get_column_dict()
        # Map from proto to template fields (proto uses VirtualActionItem base fields)
        proto_base_fields = {
            'action_name', 'description', 'estimated_duration', 
            'expected_billable_hours', 'safety_notes', 'notes'
        }
        for key in proto_base_fields:
            if key in valid_fields and hasattr(proto_action, key):
                value = getattr(proto_action, key)
                if value is not None:
                    action_data[key] = value
        
        # Set required fields
        if sequence_order is None:
            raise ValueError("sequence_order is required when creating from proto")
        action_data['sequence_order'] = sequence_order
        action_data['is_required'] = True
        action_data['minimum_staff_count'] = 1
        
        # Link to proto action
        action_data['proto_action_item_id'] = proto_action.id
        
        # Create BuildAction
        action = cls(action_data)
        
        # Copy part demands from proto (using BuildPartDemand's valid fields)
        for proto_part_demand in proto_action.proto_part_demands:
            part_data = {}
            valid_part_fields = BuildPartDemand._get_valid_fields()
            # Map proto fields to template fields
            if 'part_id' in valid_part_fields:
                part_data['part_id'] = proto_part_demand.part_id
            if 'quantity_required' in valid_part_fields:
                part_data['quantity_required'] = proto_part_demand.quantity_required
            if 'expected_cost' in valid_part_fields:
                part_data['expected_cost'] = proto_part_demand.expected_cost
            if 'notes' in valid_part_fields:
                part_data['notes'] = proto_part_demand.notes
            action.add_part_demand(part_data)
        
        # Copy tools from proto (using BuildActionTool's valid fields)
        for proto_tool in proto_action.proto_action_tools:
            tool_data = {}
            valid_tool_fields = BuildActionTool._get_valid_fields()
            # Map proto fields to template fields
            if 'tool_id' in valid_tool_fields:
                tool_data['tool_id'] = proto_tool.tool_id
            if 'quantity_required' in valid_tool_fields:
                tool_data['quantity_required'] = proto_tool.quantity_required
            if 'notes' in valid_tool_fields:
                tool_data['notes'] = proto_tool.notes
            action.add_tool(tool_data)
        
        # Proto actions don't have attachments, so nothing to copy
        
        return action
    
    @classmethod
    def from_dict(cls, action_dict: Dict[str, Any], sequence_order: Optional[int] = None) -> 'BuildAction':
        """
        Create a BuildAction from a dictionary (for custom actions from presentation layer).
        
        Args:
            action_dict: Dictionary containing action data
            sequence_order: Optional sequence order to set/override
            
        Returns:
            BuildAction: The created action wrapper
        """
        # Set sequence order if provided or if not in dict
        if sequence_order is not None:
            action_dict['sequence_order'] = sequence_order
        elif 'sequence_order' not in action_dict:
            raise ValueError("sequence_order is required when creating from dict")
        
        return cls(action_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary including part demands, tools, and attachments.
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        result = dict(self._data)
        result['part_demands'] = [pd.to_dict() for pd in self._part_demands]
        result['tools'] = [tool.to_dict() for tool in self._tools]
        result['attachments'] = [att.to_dict() for att in self._attachments]
        return result
    
    def update_from_dict(self, updates: Dict[str, Any]) -> None:
        """
        Update internal data from a dictionary, filtering to valid fields and coercing types.
        """
        if not updates:
            return
        valid_fields = self._get_valid_fields()
        for key, value in updates.items():
            if key not in valid_fields:
                continue
            # Type coercion for some known fields
            if key in ('sequence_order', 'minimum_staff_count', 'prior_revision_id', 'proto_action_item_id'):
                if value is None or value == '':
                    self._data.pop(key, None)
                else:
                    try:
                        self._data[key] = int(value)
                    except (ValueError, TypeError):
                        continue
            elif key in ('estimated_duration', 'expected_billable_hours'):
                if value is None or value == '':
                    self._data.pop(key, None)
                else:
                    try:
                        self._data[key] = float(value)
                    except (ValueError, TypeError):
                        continue
            elif key in ('is_required',):
                self._data[key] = bool(value)
            else:
                # Strings and other pass-through fields
                if value is None or value == '':
                    self._data.pop(key, None)
                else:
                    self._data[key] = value
    
    def __repr__(self):
        action_name = self.action_name or 'Unnamed'
        seq = self.sequence_order or '?'
        return f'<BuildAction "{action_name}" order={seq} parts={len(self._part_demands)} tools={len(self._tools)} attachments={len(self._attachments)}>'

