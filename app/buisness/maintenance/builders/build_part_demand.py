"""
Build Part Demand Wrapper
Lightweight wrapper around part demand dict data with validation.
"""

from typing import Dict, Any, Optional
from app.data.maintenance.templates.template_part_demands import TemplatePartDemand


class BuildPartDemand:
    """
    Wrapper for part demand data in template builder.
    Wraps a dict internally and validates against VirtualPartDemand model.
    """
    
    # Valid fields from template PartDemand
    _valid_fields = None
    
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        """
        Initialize BuildPartDemand with data dict.
        
        Args:
            data: Dictionary containing part demand fields. If None, creates empty dict.
        """
        if data is None:
            data = {}
        self._data = dict(data)
        self._ensure_valid_fields()


    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BuildPartDemand':
        """Create BuildPartDemand from dictionary."""
        part_demand = cls(data)
        part_demand._data = data
        part_demand._ensure_valid_fields()
        return part_demand
    
    @classmethod
    def _get_valid_fields(cls) -> set:
        """Get valid field names from TemplatePartDemand model, excluding builder-invalid fields."""
        if cls._valid_fields is None:
            all_fields = TemplatePartDemand.get_column_dict()
            invalid_columns = ['template_action_item_id']
            cls._valid_fields = all_fields - set(invalid_columns)
        return cls._valid_fields
    
    def _ensure_valid_fields(self):
        """Remove any invalid fields from _data."""
        valid_fields = self._get_valid_fields()
        self._data = {k: v for k, v in self._data.items() if k in valid_fields}
    
    # Getters for common fields
    @property
    def part_id(self) -> Optional[int]:
        """Get part_id."""
        return self._data.get('part_id')
    
    @part_id.setter
    def part_id(self, value: Optional[int]):
        """Set part_id."""
        if value is not None:
            self._data['part_id'] = int(value)
        elif 'part_id' in self._data:
            del self._data['part_id']
    
    @property
    def quantity_required(self) -> float:
        """Get quantity_required, defaulting to 1.0."""
        return self._data.get('quantity_required', 1.0)
    
    @quantity_required.setter
    def quantity_required(self, value: float):
        """Set quantity_required."""
        self._data['quantity_required'] = float(value)
    
    @property
    def expected_cost(self) -> Optional[float]:
        """Get expected_cost."""
        return self._data.get('expected_cost')
    
    @expected_cost.setter
    def expected_cost(self, value: Optional[float]):
        """Set expected_cost."""
        if value is not None:
            self._data['expected_cost'] = float(value)
        elif 'expected_cost' in self._data:
            del self._data['expected_cost']
    
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
    
    def update_from_dict(self, updates: Dict[str, Any]) -> None:
        """Update part demand fields from dictionary, filtering valid fields."""
        if not updates:
            return
        valid_fields = self._get_valid_fields()
        for key, value in updates.items():
            if key not in valid_fields:
                continue
            if key in ('part_id',):
                if value is None or value == '':
                    self._data.pop(key, None)
                else:
                    try:
                        self._data[key] = int(value)
                    except (ValueError, TypeError):
                        continue
            elif key in ('quantity_required', 'expected_cost'):
                if value is None or value == '':
                    self._data.pop(key, None)
                else:
                    try:
                        self._data[key] = float(value)
                    except (ValueError, TypeError):
                        continue
            else:
                # notes or other strings
                if value is None or value == '':
                    self._data.pop(key, None)
                else:
                    self._data[key] = value
    
    def __repr__(self):
        part_id = self.part_id or 'None'
        qty = self.quantity_required
        return f'<BuildPartDemand part_id={part_id} qty={qty}>'

