"""
PartDemandManager - Extension for purchasing integration

Responsibilities:
- Identify unfulfilled part demands
- Generate purchase recommendations
- Link demands to purchase orders
- Track demand fulfillment status
- Handle demand priority and urgency
- Check inventory availability
"""

from pathlib import Path
from datetime import datetime
from sqlalchemy import func
from app import db
from app.data.maintenance.base.part_demands import PartDemand
from app.data.inventory.base import (
    ActiveInventory,
    InventoryMovement,
    PurchaseOrderLine
)
from app.data.core.supply.part import Part


class PartDemandManager:
    """Extends maintenance part demand for purchasing integration"""
    
    @staticmethod
    def get_unfulfilled_demands(location_id=None, asset_type_id=None, part_id=None):
        """
        Get all part demands not yet fulfilled
        
        Args:
            location_id: Filter by location (optional)
            asset_type_id: Filter by asset type (optional)
            part_id: Filter by part (optional)
            
        Returns:
            List of PartDemand objects
        """
        query = PartDemand.query.filter(
            PartDemand.status.in_(['Planned', 'Pending'])
        )
        
        if part_id:
            query = query.filter_by(part_id=part_id)
        
        # Join through action -> maintenance_action_set -> asset if location or asset_type filtering is needed
        if location_id or asset_type_id:
            from app.data.maintenance.base.action import Action
            from app.data.maintenance.base.maintenance_action_set import MaintenanceActionSet
            from app.data.core.asset_info.asset import Asset
            
            query = query.join(Action).join(MaintenanceActionSet).join(Asset)
            
            if location_id:
                query = query.filter(Asset.major_location_id == location_id)
            
            if asset_type_id:
                query = query.filter(Asset.asset_type_id == asset_type_id)
        
        return query.order_by(PartDemand.created_at).all()
    
    @staticmethod
    def get_purchase_recommendations():
        """
        Analyze unfulfilled demands and recommend purchases
        
        Groups by part, calculates quantities, checks inventory
        
        Returns:
            List of dicts with purchase recommendations
        """
        # Get all unfulfilled demands
        demands = PartDemandManager.get_unfulfilled_demands()
        
        # Group by part
        grouped = PartDemandManager.group_demands_by_part(demands)
        
        recommendations = []
        
        for part_id, part_demands in grouped.items():
            part = Part.query.get(part_id)
            if not part:
                continue
            
            total_needed = sum(d.quantity_required for d in part_demands)
            
            # Check inventory across all locations
            inventory_available = sum(
                inv.quantity_available 
                for inv in ActiveInventory.query.filter_by(part_id=part_id).all()
            )
            
            # Calculate net need
            net_need = max(0, total_needed - inventory_available)
            
            # Check minimum stock level
            min_stock = part.minimum_stock_level or 0
            current_stock = part.current_stock_level or 0
            
            # Recommend ordering if below minimum or net need exists
            if net_need > 0 or current_stock < min_stock:
                order_quantity = max(net_need, min_stock - current_stock)
                
                recommendations.append({
                    'part_id': part_id,
                    'part_number': part.part_number,
                    'part_name': part.part_name,
                    'total_demand': total_needed,
                    'inventory_available': inventory_available,
                    'net_need': net_need,
                    'current_stock': current_stock,
                    'minimum_stock': min_stock,
                    'recommended_order_qty': order_quantity,
                    'unit_cost': part.unit_cost,
                    'estimated_cost': (part.unit_cost or 0) * order_quantity,
                    'demand_count': len(part_demands),
                    'demands': [d.id for d in part_demands],
                    'urgency': PartDemandManager.calculate_demand_urgency_bulk(part_demands)
                })
        
        # Sort by urgency (highest first)
        recommendations.sort(key=lambda x: x['urgency'], reverse=True)
        
        return recommendations
    
    @staticmethod
    def group_demands_by_part(part_demands):
        """
        Group part demands by part ID
        
        Args:
            part_demands: List of PartDemand objects
            
        Returns:
            Dict mapping part_id to list of demands
        """
        grouped = {}
        for demand in part_demands:
            if demand.part_id not in grouped:
                grouped[demand.part_id] = []
            grouped[demand.part_id].append(demand)
        
        return grouped
    
    @staticmethod
    def calculate_demand_urgency(demand_id):
        """
        Calculate priority score for a demand
        
        Args:
            demand_id: Part demand ID
            
        Returns:
            Urgency score (0-100, higher = more urgent)
        """
        demand = PartDemand.query.get(demand_id)
        if not demand:
            return 0
        
        return PartDemandManager._calculate_urgency_score(demand)
    
    @staticmethod
    def calculate_demand_urgency_bulk(demands):
        """
        Calculate average urgency for multiple demands
        
        Args:
            demands: List of PartDemand objects
            
        Returns:
            Average urgency score
        """
        if not demands:
            return 0
        
        scores = [PartDemandManager._calculate_urgency_score(d) for d in demands]
        return sum(scores) / len(scores)
    
    @staticmethod
    def _calculate_urgency_score(demand):
        """
        Internal method to calculate urgency score
        
        Factors:
        - Age of demand (older = more urgent)
        - Part availability (less available = more urgent)
        - Asset criticality (if available)
        
        Returns:
            Score 0-100
        """
        score = 0
        
        # Age factor (up to 40 points)
        age_days = (datetime.utcnow() - demand.created_at).days
        score += min(40, age_days * 2)
        
        # Availability factor (up to 40 points)
        part = demand.part
        if part:
            if part.is_out_of_stock:
                score += 40
            elif part.is_low_stock:
                score += 20
        
        # Status factor (up to 20 points)
        if demand.status == 'Planned':
            score += 10
        elif demand.status == 'Pending':
            score += 20
        
        return min(100, score)
    
    @staticmethod
    def mark_demand_fulfilled(demand_id, inventory_movement_id, user_id):
        """
        Mark demand as fulfilled when issued from inventory
        
        Args:
            demand_id: Part demand ID
            inventory_movement_id: Inventory movement ID
            user_id: User marking fulfilled
            
        Returns:
            PartDemand object
        """
        demand = PartDemand.query.get(demand_id)
        if not demand:
            raise ValueError(f"Part demand {demand_id} not found")
        
        movement = InventoryMovement.query.get(inventory_movement_id)
        if not movement:
            raise ValueError(f"Inventory movement {inventory_movement_id} not found")
        
        # Verify movement is for this demand
        if movement.part_demand_id != demand_id:
            raise ValueError("Inventory movement does not match this demand")
        
        # Mark as received (this will update status)
        if hasattr(demand, 'mark_received'):
            demand.mark_received(user_id)
        else:
            demand.status = 'Received'
            demand.updated_by_id = user_id
        
        db.session.commit()
        
        return demand
    
    @staticmethod
    def check_inventory_availability(demand_id):
        """
        Check if demand can be fulfilled from inventory
        
        Args:
            demand_id: Part demand ID
            
        Returns:
            Dict with availability info
        """
        demand = PartDemand.query.get(demand_id)
        if not demand:
            return {'error': 'Demand not found'}
        
        # Get location from action -> maintenance_action_set -> asset -> major_location_id
        location_id = None
        if hasattr(demand, 'action') and demand.action:
            if hasattr(demand.action, 'maintenance_action_set') and demand.action.maintenance_action_set:
                from app.data.core.asset_info.asset import Asset
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
    def get_demands_by_purchase_order(po_id):
        """
        Get all demands linked to a purchase order
        
        Args:
            po_id: Purchase order ID
            
        Returns:
            List of PartDemand objects
        """
        from app.data.inventory.base import PurchaseOrderHeader
        
        po = PurchaseOrderHeader.query.get(po_id)
        if not po:
            return []
        
        demands = []
        for line in po.purchase_order_lines:
            demands.extend(line.part_demands)
        
        return demands
    
    @staticmethod
    def get_demand_fulfillment_status(demand_id):
        """
        Get detailed fulfillment status for a demand
        
        Args:
            demand_id: Part demand ID
            
        Returns:
            Dict with fulfillment details
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
            for line in po_lines
            for link in line.part_demands
            if link.part_demand_id == demand_id
        )
        
        quantity_issued = sum(
            abs(mov.quantity)
            for mov in inventory_movements
            if mov.movement_type == 'Issue'
        )
        
        return {
            'demand_id': demand_id,
            'part_id': demand.part_id,
            'quantity_required': demand.quantity_required,
            'status': demand.status,
            'linked_to_po': len(po_lines) > 0,
            'po_count': len(po_lines),
            'quantity_ordered': quantity_ordered,
            'issued_from_inventory': len(inventory_movements) > 0,
            'quantity_issued': quantity_issued,
            'quantity_remaining': demand.quantity_required - quantity_issued,
            'is_fully_fulfilled': quantity_issued >= demand.quantity_required,
            'purchase_orders': [
                {
                    'po_id': line.purchase_order_id,
                    'po_number': line.purchase_order.po_number,
                    'line_id': line.id,
                    'status': line.status
                }
                for line in po_lines
            ]
        }

