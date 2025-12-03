"""
Build Action Tool Wrapper
Lightweight wrapper around action tool dict data with validation.
"""

from typing import Dict, Any, Optional
from app.data.maintenance.templates.template_action_tools import TemplateActionTool


class BuildActionTool:
    """
    Wrapper for action tool data in template builder.
    Wraps a dict internally and validates against VirtualActionTool model.
    """
    
    # Valid fields from VirtualActionTool
    _valid_fields = None
    
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        """
        Initialize BuildActionTool with data dict.
        
        Args:
            data: Dictionary containing tool fields. If None, creates empty dict.
        """
        if data is None:
            data = {}
        self._data = dict(data)
        self._ensure_valid_fields()
    
    @classmethod
    def _get_valid_fields(cls) -> set:
        """Get valid field names from TemplateActionTool model, excluding builder-invalid fields."""
        if cls._valid_fields is None:
            all_fields = TemplateActionTool.get_column_dict()
            invalid_columns = ['template_action_item_id']
            cls._valid_fields = all_fields - set(invalid_columns)
        return cls._valid_fields
    
    def _ensure_valid_fields(self):
        """Remove any invalid fields from _data."""
        valid_fields = self._get_valid_fields()
        self._data = {k: v for k, v in self._data.items() if k in valid_fields}
    
    # Getters for common fields
    @property
    def tool_id(self) -> Optional[int]:
        """Get tool_id."""
        return self._data.get('tool_id')
    
    @tool_id.setter
    def tool_id(self, value: Optional[int]):
        """Set tool_id."""
        if value is not None:
            self._data['tool_id'] = int(value)
        elif 'tool_id' in self._data:
            del self._data['tool_id']
    
    @property
    def quantity_required(self) -> int:
        """Get quantity_required, defaulting to 1."""
        return self._data.get('quantity_required', 1)
    
    @quantity_required.setter
    def quantity_required(self, value: int):
        """Set quantity_required."""
        self._data['quantity_required'] = int(value)
    
    @property
    def notes(self) -> Optional[str]:
        """Get notes."""
        return self._data.get('notes')
    
    @notes.setter
    def notes(self, value: Optional[str]):
        """Set notes."""
        if value:
            self._data['notes'] = str(value)
        elif 'notes' in self._data:
            del self._data['notes']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return dict(self._data)
    
    def __repr__(self):
        tool_id = self.tool_id or 'None'
        qty = self.quantity_required
        return f'<BuildActionTool tool_id={tool_id} qty={qty}>'
    
    def update_from_dict(self, updates: Dict[str, Any]) -> None:
        """Update tool fields from dictionary, filtering valid fields."""
        if not updates:
            return
        valid_fields = self._get_valid_fields()
        for key, value in updates.items():
            if key not in valid_fields:
                continue
            if key in ('tool_id',):
                if value is None or value == '':
                    self._data.pop(key, None)
                else:
                    try:
                        self._data[key] = int(value)
                    except (ValueError, TypeError):
                        continue
            elif key in ('quantity_required',):
                if value is None or value == '':
                    self._data.pop(key, None)
                else:
                    try:
                        self._data[key] = int(value)
                    except (ValueError, TypeError):
                        continue
            else:
                # notes or other strings
                if value is None or value == '':
                    self._data.pop(key, None)
                else:
                    self._data[key] = value

