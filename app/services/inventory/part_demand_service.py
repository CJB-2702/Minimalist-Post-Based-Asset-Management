"""
Part Demand Inventory Service
Presentation service for part demand inventory availability and fulfillment queries.
"""

from typing import Dict, List, Optional, Any
from app.data.maintenance.base.part_demands import PartDemand
from app.data.inventory.inventory import ActiveInventory, InventoryMovement
from app.data.core.asset_info.asset import Asset


class PartDemandInventoryService:
    """
    Service for part demand inventory-related queries.
    
    Provides read-only methods for:
    - Checking inventory availability for demands
    - Getting fulfillment status
    - Querying demands by purchase order
    """
    
    @staticmethod
    def check_inventory_availability(demand_id: int) -> Dict[str, Any]:
        """
        Check if demand can be fulfilled from inventory (read-only).
        
        Args:
            demand_id: Part demand ID
            
        Returns:
            Dictionary with detailed availability info
        """
        demand = PartDemand.query.get(demand_id)
        if not demand:
            return {'error': 'Demand not found'}
        
        # Get location from action -> maintenance_action_set -> asset -> major_location_id
        location_id = None
        if hasattr(demand, 'action') and demand.action:
            if hasattr(demand.action, 'maintenance_action_set') and demand.action.maintenance_action_set:
                asset = Asset.query.get(demand.action.maintenance_action_set.asset_id) if demand.action.maintenance_action_set.asset_id else None
                if asset:
                    location_id = asset.major_location_id
        
        # Check inventory at this location
        location_inventory = []
        if location_id:
            inv = ActiveInventory.query.filter_by(
                part_id=demand.part_id,
                major_location_id=location_id
            ).first()
            
            if inv:
                location_inventory.append({
                    'location_id': location_id,
                    'quantity_available': inv.quantity_available,
                    'can_fulfill': inv.quantity_available >= demand.quantity_required
                })
        
        # Check inventory at all locations
        all_inventory = ActiveInventory.query.filter_by(
            part_id=demand.part_id
        ).all()
        
        total_available = sum(inv.quantity_available for inv in all_inventory)
        
        other_locations = [
            {
                'location_id': inv.major_location_id,
                'quantity_available': inv.quantity_available,
                'can_fulfill': inv.quantity_available >= demand.quantity_required
            }
            for inv in all_inventory
            if inv.major_location_id != location_id
        ]
        
        return {
            'demand_id': demand_id,
            'part_id': demand.part_id,
            'quantity_required': demand.quantity_required,
            'preferred_location_id': location_id,
            'location_inventory': location_inventory,
            'other_locations': other_locations,
            'total_available': total_available,
            'can_fulfill_from_preferred': any(
                inv['can_fulfill'] for inv in location_inventory
            ) if location_inventory else False,
            'can_fulfill_from_any': total_available >= demand.quantity_required,
            'needs_purchase': total_available < demand.quantity_required
        }
    
    @staticmethod
    def get_demands_by_purchase_order(po_id: int) -> List[PartDemand]:
        """
        Get all demands linked to a purchase order (read-only).
        
        Args:
            po_id: Purchase order ID
            
        Returns:
            List of PartDemand objects
        """
        from app.data.inventory.ordering import PurchaseOrderHeader
        
        po = PurchaseOrderHeader.query.get(po_id)
        if not po:
            return []
        
        demands = []
        for line in po.purchase_order_lines:
            if hasattr(line, 'part_demands'):
                demands.extend(line.part_demands)
        
        return demands
    
    @staticmethod
    def get_demand_fulfillment_status(demand_id: int) -> Dict[str, Any]:
        """
        Get detailed fulfillment status for a demand (read-only).
        
        Args:
            demand_id: Part demand ID
            
        Returns:
            Dictionary with fulfillment details
        """
        demand = PartDemand.query.get(demand_id)
        if not demand:
            return {'error': 'Demand not found'}
        
        # Check if linked to PO
        po_lines = demand.purchase_order_lines if hasattr(demand, 'purchase_order_lines') else []
        
        # Check if issued from inventory
        inventory_movements = demand.inventory_movements if hasattr(demand, 'inventory_movements') else []
        
        quantity_ordered = sum(
            link.quantity_allocated
            for po_line in po_lines
            for link in (po_line.part_demand_links if hasattr(po_line, 'part_demand_links') else [])
            if link.part_demand_id == demand_id
        )
        
        quantity_issued = sum(
            abs(movement.quantity)
            for movement in inventory_movements
            if movement.movement_type == 'Issue'
        )
        
        return {
            'demand_id': demand_id,
            'quantity_required': demand.quantity_required,
            'quantity_ordered': quantity_ordered,
            'quantity_issued': quantity_issued,
            'quantity_remaining': demand.quantity_required - quantity_issued,
            'is_fulfilled': quantity_issued >= demand.quantity_required,
            'has_purchase_order': len(po_lines) > 0,
            'purchase_order_lines': [{'id': line.id, 'po_id': line.purchase_order_id} for line in po_lines],
            'inventory_movements_count': len(inventory_movements)
        }
    
    @staticmethod
    def get_unfulfilled_demands(
        part_id: Optional[int] = None,
        location_id: Optional[int] = None,
        asset_type_id: Optional[int] = None
    ) -> List[PartDemand]:
        """
        Get unfulfilled part demands with optional filters (read-only).
        
        Args:
            part_id: Optional part ID filter
            location_id: Optional location filter (via asset)
            asset_type_id: Optional asset type filter (via asset)
            
        Returns:
            List of PartDemand objects
        """
        from app.data.maintenance.base.actions import Action
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        
        query = PartDemand.query.filter(
            PartDemand.status.in_(['Planned', 'Pending'])
        )
        
        if part_id:
            query = query.filter_by(part_id=part_id)
        
        # Join through action -> maintenance_action_set -> asset if location or asset_type filtering is needed
        if location_id or asset_type_id:
            query = query.join(Action).join(MaintenanceActionSet).join(Asset)
            
            if location_id:
                query = query.filter(Asset.major_location_id == location_id)
            
            if asset_type_id:
                query = query.filter(Asset.asset_type_id == asset_type_id)
        
        return query.order_by(PartDemand.created_at).all()
    
    @staticmethod
    def get_demands_needing_purchase() -> List[PartDemand]:
        """
        Get demands that need purchase orders (read-only).
        
        Returns demands that are unfulfilled and not linked to any purchase order.
        
        Returns:
            List of PartDemand objects
        """
        unfulfilled = PartDemandInventoryService.get_unfulfilled_demands()
        
        # Filter out demands that are already linked to purchase orders
        demands_needing_purchase = []
        for demand in unfulfilled:
            has_po = False
            if hasattr(demand, 'purchase_order_lines'):
                for po_line in demand.purchase_order_lines:
                    if hasattr(po_line, 'part_demand_links'):
                        has_po = any(link.part_demand_id == demand.id for link in po_line.part_demand_links)
                        if has_po:
                            break
            
            if not has_po:
                demands_needing_purchase.append(demand)
        
        return demands_needing_purchase



