"""
Locations Package

Contains models for hierarchical inventory location tracking:
- Location: Storage areas within storerooms (shelves, racks, pallet spaces)
- Bin: Individual storage containers within locations
"""

from .location import Location
from .bin import Bin

__all__ = ['Location', 'Bin']



