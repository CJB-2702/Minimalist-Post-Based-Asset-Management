"""
InventoryManager - Business logic for inventory movements and levels

Responsibilities:
- Create inventory movements for all transactions
- Update active inventory levels
- Handle part issues to maintenance
- Process inventory adjustments
- Handle inventory transfers between locations
- Calculate average costs
- Check stock availability
- **Maintain traceability chain via initial_arrival_id and previous_movement_id**
"""

from pathlib import Path
from datetime import datetime
from app import db
from app.data.inventory.base import (
    InventoryMovement,
    ActiveInventory,
    PartArrival
)
from app.data.maintenance.base.part_demands import PartDemand
from app.data.core.supply.part import Part


class InventoryManager:
    """Manages all inventory movements and levels"""
    
    @staticmethod
    def record_arrival(part_arrival_id, user_id):
        """
        Record inventory arrival from part arrival
        
        This is the START of the traceability chain:
        - initial_arrival_id = part_arrival_id
        - previous_movement_id = null (first movement)
        
        Args:
            part_arrival_id: Part arrival ID
            user_id: User recording the arrival
            
        Returns:
            InventoryMovement object
        """
        arrival = PartArrival.query.get(part_arrival_id)
        if not arrival:
            raise ValueError(f"Part arrival {part_arrival_id} not found")
        
        if not arrival.is_accepted:
            raise ValueError("Part arrival must be accepted before recording inventory")
        
        # Get location from package
        location_id = arrival.package_header.major_location_id
        
        # Get unit cost from PO line
        unit_cost = arrival.purchase_order_line.unit_cost
        
        # Create inventory movement (ARRIVAL - start of chain)
        movement = InventoryMovement(
            part_id=arrival.part_id,
            major_location_id=location_id,
            movement_type='Arrival',
            quantity=arrival.quantity_accepted,
            movement_date=datetime.utcnow(),
            reference_type='PartArrival',
            reference_id=part_arrival_id,
            unit_cost=unit_cost,
            notes=f"Arrival from PO {arrival.purchase_order_line.purchase_order.po_number}",
            part_arrival_id=part_arrival_id,
            # TRACEABILITY CHAIN - START
            initial_arrival_id=part_arrival_id,  # This IS the initial arrival
            previous_movement_id=None,  # First in chain
            created_by_id=user_id
        )
        
        db.session.add(movement)
        
        # Update active inventory
        InventoryManager._update_active_inventory(
            arrival.part_id,
            location_id,
            arrival.quantity_accepted,
            unit_cost,
            user_id
        )
        
        # Update part current_stock_level
        part = Part.query.get(arrival.part_id)
        if part:
            part.adjust_stock(arrival.quantity_accepted, 'add', user_id)
        
        db.session.commit()
        
        return movement
    
    @staticmethod
    def issue_to_demand(part_demand_id, quantity, location_id, user_id, source_movement_id=None):
        """
        Issue parts to maintenance from inventory
        
        TRACEABILITY CHAIN:
        - Copies initial_arrival_id from source movement or active inventory
        - Sets previous_movement_id = source_movement_id
        
        Args:
            part_demand_id: Part demand ID
            quantity: Quantity to issue
            location_id: Location to issue from
            user_id: User issuing the parts
            source_movement_id: Specific movement to issue from (optional)
            
        Returns:
            InventoryMovement object
        """
        demand = PartDemand.query.get(part_demand_id)
        if not demand:
            raise ValueError(f"Part demand {part_demand_id} not found")
        
        # Check availability
        available = InventoryManager.check_availability(demand.part_id, location_id, quantity)
        if not available['available']:
            raise ValueError(
                f"Insufficient inventory: need {quantity}, have {available['quantity_available']}"
            )
        
        # Get traceability info from most recent arrival for this part/location
        initial_arrival_id = None
        if source_movement_id:
            source = InventoryMovement.query.get(source_movement_id)
            if source:
                initial_arrival_id = source.initial_arrival_id
        else:
            # Find most recent arrival movement for this part/location
            last_arrival = InventoryMovement.query.filter_by(
                part_id=demand.part_id,
                major_location_id=location_id
            ).filter(
                InventoryMovement.initial_arrival_id.isnot(None)
            ).order_by(InventoryMovement.movement_date.desc()).first()
            
            if last_arrival:
                initial_arrival_id = last_arrival.initial_arrival_id
        
        # Get average cost from active inventory
        active_inv = ActiveInventory.query.filter_by(
            part_id=demand.part_id,
            major_location_id=location_id
        ).first()
        
        unit_cost = active_inv.unit_cost_avg if active_inv else None
        
        # Create inventory movement (ISSUE)
        movement = InventoryMovement(
            part_id=demand.part_id,
            major_location_id=location_id,
            movement_type='Issue',
            quantity=-quantity,  # Negative for issue
            movement_date=datetime.utcnow(),
            reference_type='PartDemand',
            reference_id=part_demand_id,
            unit_cost=unit_cost,
            notes=f"Issued to maintenance action",
            part_demand_id=part_demand_id,
            # TRACEABILITY CHAIN - PRESERVE
            initial_arrival_id=initial_arrival_id,
            previous_movement_id=source_movement_id,
            created_by_id=user_id
        )
        
        db.session.add(movement)
        
        # Update active inventory
        InventoryManager._update_active_inventory(
            demand.part_id,
            location_id,
            -quantity,
            unit_cost,
            user_id
        )
        
        # Update part current_stock_level
        part = Part.query.get(demand.part_id)
        if part:
            part.adjust_stock(quantity, 'subtract', user_id)
        
        # Mark demand as received
        if hasattr(demand, 'mark_received'):
            demand.mark_received(user_id)
        
        db.session.commit()
        
        return movement
    
    @staticmethod
    def adjust_inventory(part_id, location_id, quantity, reason, user_id, 
                        initial_arrival_id=None, source_movement_id=None):
        """
        Manual inventory adjustment
        
        TRACEABILITY CHAIN:
        - Maintains initial_arrival_id if adjusting existing inventory
        - Links previous_movement_id if adjustment relates to prior movement
        
        Args:
            part_id: Part ID
            location_id: Location ID
            quantity: Adjustment quantity (positive or negative)
            reason: Reason for adjustment
            user_id: User making adjustment
            initial_arrival_id: Original arrival to maintain chain (optional)
            source_movement_id: Previous movement (optional)
            
        Returns:
            InventoryMovement object
        """
        # Get current inventory to preserve traceability if not provided
        if not initial_arrival_id:
            last_movement = InventoryMovement.query.filter_by(
                part_id=part_id,
                major_location_id=location_id
            ).filter(
                InventoryMovement.initial_arrival_id.isnot(None)
            ).order_by(InventoryMovement.movement_date.desc()).first()
            
            if last_movement:
                initial_arrival_id = last_movement.initial_arrival_id
        
        # Get average cost
        active_inv = ActiveInventory.query.filter_by(
            part_id=part_id,
            major_location_id=location_id
        ).first()
        
        unit_cost = active_inv.unit_cost_avg if active_inv else None
        
        # Create inventory movement (ADJUSTMENT)
        movement = InventoryMovement(
            part_id=part_id,
            major_location_id=location_id,
            movement_type='Adjustment',
            quantity=quantity,
            movement_date=datetime.utcnow(),
            reference_type='Manual',
            unit_cost=unit_cost,
            notes=reason,
            # TRACEABILITY CHAIN - MAINTAIN
            initial_arrival_id=initial_arrival_id,
            previous_movement_id=source_movement_id,
            created_by_id=user_id
        )
        
        db.session.add(movement)
        
        # Update active inventory
        InventoryManager._update_active_inventory(
            part_id,
            location_id,
            quantity,
            unit_cost,
            user_id
        )
        
        # Update part current_stock_level
        part = Part.query.get(part_id)
        if part:
            if quantity > 0:
                part.adjust_stock(quantity, 'add', user_id)
            else:
                part.adjust_stock(abs(quantity), 'subtract', user_id)
        
        db.session.commit()
        
        return movement
    
    @staticmethod
    def transfer_between_locations(part_id, from_location_id, to_location_id, 
                                   quantity, user_id, source_movement_id=None):
        """
        Transfer inventory between locations
        
        TRACEABILITY CHAIN:
        - Preserves initial_arrival_id from source location
        - Sets previous_movement_id = source_movement_id
        
        Args:
            part_id: Part ID
            from_location_id: Source location
            to_location_id: Destination location
            quantity: Quantity to transfer
            user_id: User performing transfer
            source_movement_id: Specific movement to transfer from (optional)
            
        Returns:
            Tuple of (from_movement, to_movement)
        """
        # Check availability at source
        available = InventoryManager.check_availability(part_id, from_location_id, quantity)
        if not available['available']:
            raise ValueError(
                f"Insufficient inventory at source: need {quantity}, have {available['quantity_available']}"
            )
        
        # Get traceability from source
        initial_arrival_id = None
        if source_movement_id:
            source = InventoryMovement.query.get(source_movement_id)
            if source:
                initial_arrival_id = source.initial_arrival_id
        else:
            # Find most recent movement at source location
            last_movement = InventoryMovement.query.filter_by(
                part_id=part_id,
                major_location_id=from_location_id
            ).filter(
                InventoryMovement.initial_arrival_id.isnot(None)
            ).order_by(InventoryMovement.movement_date.desc()).first()
            
            if last_movement:
                initial_arrival_id = last_movement.initial_arrival_id
        
        # Get average cost from source
        active_inv = ActiveInventory.query.filter_by(
            part_id=part_id,
            major_location_id=from_location_id
        ).first()
        
        unit_cost = active_inv.unit_cost_avg if active_inv else None
        
        # Create FROM movement (negative)
        from_movement = InventoryMovement(
            part_id=part_id,
            major_location_id=from_location_id,
            movement_type='Transfer',
            quantity=-quantity,
            movement_date=datetime.utcnow(),
            reference_type='Transfer',
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            unit_cost=unit_cost,
            notes=f"Transfer to location {to_location_id}",
            # TRACEABILITY CHAIN - PRESERVE
            initial_arrival_id=initial_arrival_id,
            previous_movement_id=source_movement_id,
            created_by_id=user_id
        )
        
        db.session.add(from_movement)
        db.session.flush()  # Get from_movement.id
        
        # Create TO movement (positive)
        to_movement = InventoryMovement(
            part_id=part_id,
            major_location_id=to_location_id,
            movement_type='Transfer',
            quantity=quantity,
            movement_date=datetime.utcnow(),
            reference_type='Transfer',
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            unit_cost=unit_cost,
            notes=f"Transfer from location {from_location_id}",
            # TRACEABILITY CHAIN - PRESERVE AND LINK
            initial_arrival_id=initial_arrival_id,  # Same original arrival
            previous_movement_id=from_movement.id,  # Link to from_movement
            created_by_id=user_id
        )
        
        db.session.add(to_movement)
        
        # Update active inventory at both locations
        InventoryManager._update_active_inventory(
            part_id, from_location_id, -quantity, unit_cost, user_id
        )
        InventoryManager._update_active_inventory(
            part_id, to_location_id, quantity, unit_cost, user_id
        )
        
        db.session.commit()
        
        return (from_movement, to_movement)
    
    @staticmethod
    def return_from_demand(part_demand_id, quantity, condition, user_id):
        """
        Return unused parts from maintenance
        
        TRACEABILITY CHAIN:
        - Traces back to original issue movement to maintain chain
        - Preserves initial_arrival_id from original issue
        
        Args:
            part_demand_id: Part demand ID
            quantity: Quantity returned
            condition: Condition of returned parts
            user_id: User processing return
            
        Returns:
            InventoryMovement object
        """
        demand = PartDemand.query.get(part_demand_id)
        if not demand:
            raise ValueError(f"Part demand {part_demand_id} not found")
        
        # Find original issue movement
        issue_movement = InventoryMovement.query.filter_by(
            part_demand_id=part_demand_id,
            movement_type='Issue'
        ).first()
        
        if not issue_movement:
            raise ValueError(f"No issue movement found for demand {part_demand_id}")
        
        # Use same location as original issue
        location_id = issue_movement.major_location_id
        
        # Create return movement
        movement = InventoryMovement(
            part_id=demand.part_id,
            major_location_id=location_id,
            movement_type='Return',
            quantity=quantity,
            movement_date=datetime.utcnow(),
            reference_type='PartDemand',
            reference_id=part_demand_id,
            unit_cost=issue_movement.unit_cost,
            notes=f"Returned from maintenance - Condition: {condition}",
            part_demand_id=part_demand_id,
            # TRACEABILITY CHAIN - MAINTAIN FROM ORIGINAL ISSUE
            initial_arrival_id=issue_movement.initial_arrival_id,
            previous_movement_id=issue_movement.id,
            created_by_id=user_id
        )
        
        db.session.add(movement)
        
        # Update active inventory
        InventoryManager._update_active_inventory(
            demand.part_id,
            location_id,
            quantity,
            issue_movement.unit_cost,
            user_id
        )
        
        # Update part current_stock_level
        part = Part.query.get(demand.part_id)
        if part:
            part.adjust_stock(quantity, 'add', user_id)
        
        db.session.commit()
        
        return movement
    
    @staticmethod
    def check_availability(part_id, location_id, quantity):
        """
        Check if parts are available at location
        
        Args:
            part_id: Part ID
            location_id: Location ID
            quantity: Required quantity
            
        Returns:
            Dict with availability info
        """
        active_inv = ActiveInventory.query.filter_by(
            part_id=part_id,
            major_location_id=location_id
        ).first()
        
        if not active_inv:
            return {
                'available': False,
                'quantity_on_hand': 0,
                'quantity_allocated': 0,
                'quantity_available': 0,
                'requested': quantity
            }
        
        return {
            'available': active_inv.quantity_available >= quantity,
            'quantity_on_hand': active_inv.quantity_on_hand,
            'quantity_allocated': active_inv.quantity_allocated,
            'quantity_available': active_inv.quantity_available,
            'requested': quantity
        }
    
    @staticmethod
    def get_inventory_by_location(location_id):
        """
        Get all inventory at a location
        
        Args:
            location_id: Location ID
            
        Returns:
            List of ActiveInventory objects
        """
        return ActiveInventory.query.filter_by(
            major_location_id=location_id
        ).filter(
            ActiveInventory.quantity_on_hand > 0
        ).all()
    
    @staticmethod
    def get_inventory_by_part(part_id):
        """
        Get inventory for a part across all locations
        
        Args:
            part_id: Part ID
            
        Returns:
            List of ActiveInventory objects
        """
        return ActiveInventory.query.filter_by(
            part_id=part_id
        ).filter(
            ActiveInventory.quantity_on_hand > 0
        ).all()
    
    @staticmethod
    def allocate_to_demand(part_demand_id, quantity, location_id, user_id):
        """
        Reserve inventory for demand
        
        Args:
            part_demand_id: Part demand ID
            quantity: Quantity to allocate
            location_id: Location ID
            user_id: User allocating
            
        Returns:
            ActiveInventory object
        """
        demand = PartDemand.query.get(part_demand_id)
        if not demand:
            raise ValueError(f"Part demand {part_demand_id} not found")
        
        active_inv = ActiveInventory.query.filter_by(
            part_id=demand.part_id,
            major_location_id=location_id
        ).first()
        
        if not active_inv:
            raise ValueError(f"No inventory found for part at location")
        
        if active_inv.quantity_available < quantity:
            raise ValueError(f"Insufficient available inventory")
        
        active_inv.quantity_allocated += quantity
        active_inv.updated_by_id = user_id
        
        db.session.commit()
        
        return active_inv
    
    @staticmethod
    def deallocate_from_demand(part_demand_id, quantity, location_id, user_id):
        """
        Release reserved inventory
        
        Args:
            part_demand_id: Part demand ID
            quantity: Quantity to deallocate
            location_id: Location ID
            user_id: User deallocating
            
        Returns:
            ActiveInventory object
        """
        demand = PartDemand.query.get(part_demand_id)
        if not demand:
            raise ValueError(f"Part demand {part_demand_id} not found")
        
        active_inv = ActiveInventory.query.filter_by(
            part_id=demand.part_id,
            major_location_id=location_id
        ).first()
        
        if active_inv:
            active_inv.quantity_allocated = max(0, active_inv.quantity_allocated - quantity)
            active_inv.updated_by_id = user_id
            db.session.commit()
        
        return active_inv
    
    @staticmethod
    def get_movement_history(movement_id):
        """
        Get complete chain of movements back to arrival
        
        Args:
            movement_id: Starting movement ID
            
        Returns:
            List of InventoryMovement objects (ordered newest to oldest)
        """
        movement = InventoryMovement.query.get(movement_id)
        if not movement:
            return []
        
        return movement.get_movement_chain()
    
    @staticmethod
    def get_movements_from_arrival(arrival_id):
        """
        Get all movements originating from an arrival
        
        Args:
            arrival_id: Part arrival ID
            
        Returns:
            List of InventoryMovement objects
        """
        return InventoryMovement.query.filter_by(
            initial_arrival_id=arrival_id
        ).order_by(InventoryMovement.movement_date).all()
    
    @staticmethod
    def _update_active_inventory(part_id, location_id, quantity, unit_cost, user_id):
        """
        Update or create active inventory record
        
        Internal method for maintaining inventory levels
        
        Args:
            part_id: Part ID
            location_id: Location ID
            quantity: Quantity change (positive or negative)
            unit_cost: Unit cost for average calculation
            user_id: User ID
        """
        active_inv = ActiveInventory.query.filter_by(
            part_id=part_id,
            major_location_id=location_id
        ).first()
        
        if not active_inv:
            # Create new inventory record
            active_inv = ActiveInventory(
                part_id=part_id,
                major_location_id=location_id,
                quantity_on_hand=max(0, quantity),
                quantity_allocated=0,
                unit_cost_avg=unit_cost,
                last_movement_date=datetime.utcnow(),
                created_by_id=user_id
            )
            db.session.add(active_inv)
        else:
            # Update existing inventory
            old_quantity = active_inv.quantity_on_hand
            old_cost = active_inv.unit_cost_avg or 0
            
            # Adjust quantity
            active_inv.quantity_on_hand = max(0, active_inv.quantity_on_hand + quantity)
            active_inv.last_movement_date = datetime.utcnow()
            active_inv.updated_by_id = user_id
            
            # Update average cost (weighted average for additions)
            if quantity > 0 and unit_cost and old_quantity >= 0:
                total_value = (old_quantity * old_cost) + (quantity * unit_cost)
                total_quantity = old_quantity + quantity
                if total_quantity > 0:
                    active_inv.unit_cost_avg = total_value / total_quantity
            elif unit_cost:
                active_inv.unit_cost_avg = unit_cost

