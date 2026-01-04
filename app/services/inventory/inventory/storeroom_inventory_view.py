"""
Storeroom Inventory View Service

Provides aggregated inventory summary for a specific storeroom.
Includes part details and 6-month average cost.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from app import db
from app.data.inventory.inventory import ActiveInventory
from app.data.inventory.inventory import Storeroom
from app.data.core.supply.part_definition import PartDefinition
from app.data.inventory.inventory import InventoryMovement


class StoreroomInventoryView:
    """
    Service for storeroom-level inventory aggregation.
    
    Provides methods to get aggregated inventory data for a storeroom,
    including part details and 6-month average costs.
    """
    
    @staticmethod
    def get_storeroom_summary(storeroom_id: int) -> List[Dict[str, Any]]:
        """
        Get aggregated inventory summary for a storeroom.
        
        Args:
            storeroom_id: Storeroom ID
            
        Returns:
            List of dictionaries with inventory summary per part
        """
        # Get all active inventory for this storeroom
        inventory_records = ActiveInventory.query.filter_by(
            storeroom_id=storeroom_id
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
                    'bin_count': 0,
                    'six_month_avg_cost': None
                }
            
            summary = part_summaries[part_id]
            summary['total_quantity_on_hand'] += inv.quantity_on_hand
            summary['total_quantity_allocated'] += inv.quantity_allocated
            summary['total_quantity_available'] += inv.quantity_available
            summary['total_value'] += inv.total_value
            summary['bin_count'] += 1
        
        # Calculate 6-month average cost for each part
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        for part_id, summary in part_summaries.items():
            # Get movements for this part at this storeroom in last 6 months
            # Find movements that affected inventory in this storeroom
            movements = db.session.query(InventoryMovement).join(
                ActiveInventory,
                and_(
                    ActiveInventory.part_id == InventoryMovement.part_id,
                    ActiveInventory.storeroom_id == storeroom_id
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
    def get_storeroom_total_value(storeroom_id: int) -> float:
        """
        Get total inventory value for a storeroom.
        
        Args:
            storeroom_id: Storeroom ID
            
        Returns:
            Total value as float
        """
        summary = StoreroomInventoryView.get_storeroom_summary(storeroom_id)
        return sum(item['total_value'] for item in summary)
    
    @staticmethod
    def get_storeroom_part_count(storeroom_id: int) -> int:
        """
        Get count of unique parts in storeroom.
        
        Args:
            storeroom_id: Storeroom ID
            
        Returns:
            Count of unique parts
        """
        return db.session.query(func.count(func.distinct(ActiveInventory.part_id)))\
            .filter_by(storeroom_id=storeroom_id).scalar() or 0
    
    @staticmethod
    def get_storeroom_bin_count(storeroom_id: int) -> int:
        """
        Get count of bins in storeroom.
        
        Args:
            storeroom_id: Storeroom ID
            
        Returns:
            Count of bins
        """
        return ActiveInventory.query.filter_by(storeroom_id=storeroom_id).count()

