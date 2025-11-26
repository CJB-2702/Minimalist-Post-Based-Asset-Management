"""
Build Attachment Wrapper
Lightweight wrapper around attachment reference dict data.
"""

from typing import Dict, Any, Optional
from app.data.maintenance.templates.template_action_set_attachments import TemplateActionSetAttachment
from app.data.maintenance.templates.template_action_attachments import TemplateActionAttachment


class BuildAttachment:
    """
    Wrapper for attachment reference data in template builder.
    Wraps a dict internally and provides getters/setters.
    Can represent either action-set level or action level attachments.
    """
    _valid_fields = None

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        """
        Initialize BuildAttachment with data dict.
        
        Args:
            data: Dictionary containing attachment reference fields. If None, creates empty dict.
        """
        if data is None:
            data = {}
        self._data = dict(data)
        self._ensure_valid_fields()

    @classmethod
    def _get_valid_fields(cls) -> set:
        """Get valid field names from attachment reference models, excluding builder-invalid fields."""
        if cls._valid_fields is None:
            # Use TemplateActionSetAttachment as base (both have same fields)
            all_fields = TemplateActionSetAttachment.get_column_dict()
            invalid_columns = ['template_action_set_id', 'template_action_item_id']
            cls._valid_fields = all_fields - set(invalid_columns)
        return cls._valid_fields

    def _ensure_valid_fields(self):
        """Remove any invalid fields from _data."""
        valid_fields = self._get_valid_fields()
        self._data = {k: v for k, v in self._data.items() if k in valid_fields}

    # Getters and setters for common fields
    @property
    def attachment_id(self) -> Optional[int]:
        """Get attachment_id."""
        return self._data.get('attachment_id')
    
    @attachment_id.setter
    def attachment_id(self, value: Optional[int]):
        """Set attachment_id."""
        if value is not None:
            self._data['attachment_id'] = int(value)
        elif 'attachment_id' in self._data:
            del self._data['attachment_id']

    @property
    def attachment_type(self) -> Optional[str]:
        """Get attachment_type."""
        return self._data.get('attachment_type')
    
    @attachment_type.setter
    def attachment_type(self, value: Optional[str]):
        """Set attachment_type."""
        if value:
            self._data['attachment_type'] = str(value)
        elif 'attachment_type' in self._data:
            del self._data['attachment_type']

    @property
    def caption(self) -> Optional[str]:
        """Get caption."""
        return self._data.get('caption')
    
    @caption.setter
    def caption(self, value: Optional[str]):
        """Set caption."""
        if value:
            self._data['caption'] = str(value)
        elif 'caption' in self._data:
            del self._data['caption']

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
    def is_required(self) -> Optional[bool]:
        """Get is_required."""
        return self._data.get('is_required')
    
    @is_required.setter
    def is_required(self, value: Optional[bool]):
        """Set is_required."""
        if value is not None:
            self._data['is_required'] = bool(value)
        elif 'is_required' in self._data:
            del self._data['is_required']

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return dict(self._data)

    def __repr__(self):
        att_id = self.attachment_id or '?'
        att_type = self.attachment_type or '?'
        return f'<BuildAttachment attachment_id={att_id} type={att_type}>'

