"""
Major Location Inventory View Service

Provides aggregated inventory summary for a major location.
Aggregates across all storerooms within the location.
Includes part details and 6-month average cost.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from app import db
from app.data.inventory.inventory import ActiveInventory, Storeroom
from app.data.core.supply.part_definition import PartDefinition
from app.data.inventory.inventory import InventoryMovement
from app.data.core.major_location import MajorLocation


class MajorLocationInventoryView:
    """
    Service for major location-level inventory aggregation.
    
    Provides methods to get aggregated inventory data for a major location,
    aggregating across all storerooms within the location.
    """
    
    @staticmethod
    def get_location_summary(major_location_id: int) -> List[Dict[str, Any]]:
        """
        Get aggregated inventory summary for a major location.
        
        Aggregates inventory from all storerooms within the location.
        
        Args:
            major_location_id: Major location ID
            
        Returns:
            List of dictionaries with inventory summary per part
        """
        # Get all storerooms for this location
        storerooms = Storeroom.query.filter_by(
            major_location_id=major_location_id,
            is_active=True
        ).all()
        
        storeroom_ids = [s.id for s in storerooms]
        
        if not storeroom_ids:
            return []
        
        # Get all active inventory for storerooms in this location
        inventory_records = ActiveInventory.query.filter(
            ActiveInventory.storeroom_id.in_(storeroom_ids)
        ).all()
        
        # Group by part_id and aggregate
        part_summaries = {}
        
        for inv in inventory_records:
            part_id = inv.part_id
            
            if part_id not in part_summaries:
                part = PartDefinition.query.get(part_id)
                part_summaries[part_id] = {
                    'part_id': part_id,
                    'part_number': part.part_number if part else None,
                    'part_name': part.part_name if part else None,
                    'total_quantity_on_hand': 0.0,
                    'total_quantity_allocated': 0.0,
                    'total_quantity_available': 0.0,
                    'total_value': 0.0,
                    'storeroom_count': set(),
                    'bin_count': 0,
                    'six_month_avg_cost': None
                }
            
            summary = part_summaries[part_id]
            summary['total_quantity_on_hand'] += inv.quantity_on_hand
            summary['total_quantity_allocated'] += inv.quantity_allocated
            summary['total_quantity_available'] += inv.quantity_available
            summary['total_value'] += inv.total_value
            summary['storeroom_count'].add(inv.storeroom_id)
            summary['bin_count'] += 1
        
        # Convert storeroom_count sets to counts
        for summary in part_summaries.values():
            summary['storeroom_count'] = len(summary['storeroom_count'])
        
        # Calculate 6-month average cost for each part
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        for part_id, summary in part_summaries.items():
            # Get movements for this part at storerooms in this location in last 6 months
            movements = db.session.query(InventoryMovement).join(
                ActiveInventory,
                ActiveInventory.part_id == InventoryMovement.part_id
            ).join(
                Storeroom,
                and_(
                    Storeroom.id == ActiveInventory.storeroom_id,
                    Storeroom.major_location_id == major_location_id
                )
            ).filter(
                and_(
                    InventoryMovement.part_id == part_id,
                    InventoryMovement.movement_date >= six_months_ago,
                    InventoryMovement.movement_type.in_(['Arrival', 'Transfer'])
                )
            ).all()
            
            if movements:
                # Calculate weighted average cost
                total_cost = sum(m.unit_cost * abs(m.quantity) for m in movements if m.unit_cost)
                total_quantity = sum(abs(m.quantity) for m in movements)
                
                if total_quantity > 0:
                    summary['six_month_avg_cost'] = total_cost / total_quantity
        
        return list(part_summaries.values())
    
    @staticmethod
    def get_location_total_value(major_location_id: int) -> float:
        """
        Get total inventory value for a major location.
        
        Args:
            major_location_id: Major location ID
            
        Returns:
            Total value as float
        """
        summary = MajorLocationInventoryView.get_location_summary(major_location_id)
        return sum(item['total_value'] for item in summary)
    
    @staticmethod
    def get_location_part_count(major_location_id: int) -> int:
        """
        Get count of unique parts in location.
        
        Args:
            major_location_id: Major location ID
            
        Returns:
            Count of unique parts
        """
        storerooms = Storeroom.query.filter_by(
            major_location_id=major_location_id,
            is_active=True
        ).all()
        
        storeroom_ids = [s.id for s in storerooms]
        
        if not storeroom_ids:
            return 0
        
        return db.session.query(func.count(func.distinct(ActiveInventory.part_id)))\
            .filter(ActiveInventory.storeroom_id.in_(storeroom_ids)).scalar() or 0
    
    @staticmethod
    def get_location_storeroom_count(major_location_id: int) -> int:
        """
        Get count of storerooms in location.
        
        Args:
            major_location_id: Major location ID
            
        Returns:
            Count of storerooms
        """
        return Storeroom.query.filter_by(
            major_location_id=major_location_id,
            is_active=True
        ).count()

