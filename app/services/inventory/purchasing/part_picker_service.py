"""
Part Picker Service
Service for part picker portal searches across different modes.
"""

from typing import List, Dict, Optional, Any
from app import db
from app.data.core.supply.part_definition import PartDefinition
from app.data.inventory.inventory import ActiveInventory
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.actions import Action
from sqlalchemy import func, or_


class PartPickerService:
    """Service for part picker searches"""
    
    @staticmethod
    def search_by_description(search_term: str = '', category: Optional[str] = None, 
                              manufacturer: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search parts by description with optional filters.
        
        Args:
            search_term: Search term for part name, number, or description
            category: Optional category filter
            manufacturer: Optional manufacturer filter
            limit: Maximum number of results
            
        Returns:
            List of part dictionaries with metadata
        """
        query = PartDefinition.query.filter(PartDefinition.status == 'Active')
        
        if search_term:
            query = query.filter(
                or_(
                    PartDefinition.part_number.ilike(f'%{search_term}%'),
                    PartDefinition.part_name.ilike(f'%{search_term}%'),
                    PartDefinition.description.ilike(f'%{search_term}%')
                )
            )
        
        if category:
            query = query.filter(PartDefinition.category == category)
        
        if manufacturer:
            query = query.filter(PartDefinition.manufacturer.ilike(f'%{manufacturer}%'))
        
        parts = query.order_by(PartDefinition.part_name).limit(limit).all()
        
        results = []
        for part in parts:
            results.append({
                'id': part.id,
                'part_number': part.part_number,
                'part_name': part.part_name,
                'description': part.description or '',
                'category': part.category or '',
                'manufacturer': part.manufacturer or '',
                'last_unit_cost': part.last_unit_cost or 0.0,
                'unit_of_measure': part.unit_of_measure or ''
            })
        
        return results
    
    @staticmethod
    def search_by_inventory(search_term: str = '', location_id: Optional[int] = None,
                           stock_level: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search parts by inventory location and stock levels.
        
        Args:
            search_term: Search term for part ID or location
            location_id: Optional location filter
            stock_level: Optional stock level filter ('low', 'out', 'good')
            limit: Maximum number of results
            
        Returns:
            List of part dictionaries with inventory metadata
        """
        # Start with parts that have inventory
        query = db.session.query(
            PartDefinition,
            func.sum(ActiveInventory.quantity_on_hand).label('total_stock'),
            func.max(ActiveInventory.storeroom_id).label('sample_storeroom_id')
        ).join(
            ActiveInventory, PartDefinition.id == ActiveInventory.part_id
        ).filter(
            PartDefinition.status == 'Active'
        )
        
        if search_term:
            query = query.filter(
                or_(
                    PartDefinition.part_number.ilike(f'%{search_term}%'),
                    PartDefinition.part_name.ilike(f'%{search_term}%')
                )
            )
        
        if location_id:
            # Filter by location via storeroom
            from app.data.core.storeroom import Storeroom
            query = query.join(
                Storeroom, ActiveInventory.storeroom_id == Storeroom.id
            ).filter(Storeroom.major_location_id == location_id)
        
        query = query.group_by(PartDefinition.id)
        
        # Apply stock level filter
        if stock_level == 'low':
            query = query.having(func.sum(ActiveInventory.quantity_on_hand) > 0)
            query = query.having(func.sum(ActiveInventory.quantity_on_hand) <= 10)
        elif stock_level == 'out':
            query = query.having(func.sum(ActiveInventory.quantity_on_hand) <= 0)
        elif stock_level == 'good':
            query = query.having(func.sum(ActiveInventory.quantity_on_hand) > 10)
        
        results_raw = query.order_by(PartDefinition.part_name).limit(limit).all()
        
        results = []
        for part, total_stock, storeroom_id in results_raw:
            stock_status = 'out' if total_stock <= 0 else ('low' if total_stock <= 10 else 'good')
            
            results.append({
                'id': part.id,
                'part_number': part.part_number,
                'part_name': part.part_name,
                'description': part.description or '',
                'category': part.category or '',
                'total_stock': float(total_stock or 0),
                'stock_status': stock_status,
                'last_unit_cost': part.last_unit_cost or 0.0,
                'storeroom_id': storeroom_id
            })
        
        return results
    
    @staticmethod
    def search_by_maintenance_event(search_term: str = '', event_type: Optional[str] = None,
                                   limit: int = 20) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Search parts by maintenance event demands.
        
        Args:
            search_term: Search term for maintenance events or parts
            event_type: Optional event type filter
            limit: Maximum number of results
            
        Returns:
            Tuple of (list of part dictionaries, preview summary dict)
        """
        # Query part demands grouped by part
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from app.data.core.event_info.event import Event
        
        query = db.session.query(
            PartDefinition,
            func.sum(PartDemand.quantity_required).label('total_demand'),
            func.count(PartDemand.id).label('demand_count'),
            func.count(func.distinct(Action.maintenance_action_set_id)).label('event_count')
        ).join(
            PartDemand, PartDefinition.id == PartDemand.part_id
        ).join(
            Action, PartDemand.action_id == Action.id
        ).join(
            MaintenanceActionSet, Action.maintenance_action_set_id == MaintenanceActionSet.id
        ).join(
            Event, MaintenanceActionSet.event_id == Event.id
        ).filter(
            PartDefinition.status == 'Active',
            PartDemand.status.in_(['Planned', 'Pending Manager Approval', 'Pending Inventory Approval', 'Ordered'])
        )
        
        if search_term:
            query = query.filter(
                or_(
                    PartDefinition.part_number.ilike(f'%{search_term}%'),
                    PartDefinition.part_name.ilike(f'%{search_term}%')
                )
            )
        
        # Note: event_type filter not implemented yet as all maintenance events are same type
        # Can filter by MaintenanceActionSet.status if needed
        
        # Group by part
        query = query.group_by(PartDefinition.id)
        
        results_raw = query.order_by(func.sum(PartDemand.quantity_required).desc()).limit(limit).all()
        
        results = []
        total_demand = 0
        total_events = set()
        total_cost = 0.0
        
        for part, total_demand_qty, demand_count, event_count in results_raw:
            total_demand += total_demand_qty
            total_cost += (total_demand_qty * (part.last_unit_cost or 0.0))
            
            results.append({
                'id': part.id,
                'part_number': part.part_number,
                'part_name': part.part_name,
                'description': part.description or '',
                'category': part.category or '',
                'demand_quantity': float(total_demand_qty),
                'demand_count': demand_count,
                'event_count': event_count,
                'last_unit_cost': part.last_unit_cost or 0.0
            })
        
        # Calculate preview summary
        preview = {
            'total_demand': total_demand,
            'total_events': len(set([r['event_count'] for r in results])),
            'total_cost': total_cost
        }
        
        return results, preview

