"""
Global Inventory View Service

Provides aggregated inventory summary across all locations.
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


class GlobalInventoryView:
    """
    Service for global inventory aggregation.
    
    Provides methods to get aggregated inventory data across all locations,
    including part details and 6-month average costs.
    """
    
    @staticmethod
    def get_global_summary() -> List[Dict[str, Any]]:
        """
        Get aggregated inventory summary across all locations.
        
        Returns:
            List of dictionaries with inventory summary per part
        """
        # Get all active inventory
        inventory_records = ActiveInventory.query.join(
            Storeroom
        ).filter(
            Storeroom.is_active == True
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
                    'major_location_count': set(),
                    'storeroom_count': set(),
                    'bin_count': 0,
                    'six_month_avg_cost': None
                }
            
            summary = part_summaries[part_id]
            summary['total_quantity_on_hand'] += inv.quantity_on_hand
            summary['total_quantity_allocated'] += inv.quantity_allocated
            summary['total_quantity_available'] += inv.quantity_available
            summary['total_value'] += inv.total_value
            summary['major_location_count'].add(inv.major_location_id)
            summary['storeroom_count'].add(inv.storeroom_id)
            summary['bin_count'] += 1
        
        # Convert sets to counts
        for summary in part_summaries.values():
            summary['major_location_count'] = len(summary['major_location_count'])
            summary['storeroom_count'] = len(summary['storeroom_count'])
        
        # Calculate 6-month average cost for each part
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        for part_id, summary in part_summaries.items():
            # Get movements for this part in last 6 months
            movements = InventoryMovement.query.filter(
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
    def get_global_total_value() -> float:
        """
        Get total inventory value across all locations.
        
        Returns:
            Total value as float
        """
        summary = GlobalInventoryView.get_global_summary()
        return sum(item['total_value'] for item in summary)
    
    @staticmethod
    def get_global_part_count() -> int:
        """
        Get count of unique parts globally.
        
        Returns:
            Count of unique parts
        """
        return db.session.query(func.count(func.distinct(ActiveInventory.part_id)))\
            .join(Storeroom).filter(Storeroom.is_active == True).scalar() or 0
    
    @staticmethod
    def get_global_location_count() -> int:
        """
        Get count of major locations with inventory.
        
        Returns:
            Count of major locations
        """
        return db.session.query(func.count(func.distinct(Storeroom.major_location_id)))\
            .filter(Storeroom.is_active == True).scalar() or 0
    
    @staticmethod
    def get_global_storeroom_count() -> int:
        """
        Get count of storerooms with inventory.
        
        Returns:
            Count of storerooms
        """
        return db.session.query(func.count(func.distinct(ActiveInventory.storeroom_id)))\
            .join(Storeroom).filter(Storeroom.is_active == True).scalar() or 0






