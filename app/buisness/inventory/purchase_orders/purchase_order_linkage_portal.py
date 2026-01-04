"""
Purchase Order Linkage Portal Context

Business logic for linking part demands to PO lines.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import joinedload

from app import db
from app.data.core.asset_info.asset import Asset
from app.data.inventory.ordering.part_demand_purchase_order_line import PartDemandPurchaseOrderLink
from app.data.inventory.ordering.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.maintenance.base.part_demands import PartDemand
from app.logger import get_logger

logger = get_logger("asset_management.buisness.inventory.purchase_orders.linkage_portal")


@dataclass
class POLineWithDemands:
    """PO Line with its linked and linkable demands"""
    po_line: PurchaseOrderLine
    linked_demands: list[PartDemand]
    linkable_demands: list[PartDemand]
    quantity_available: float
    allocation_percentage: float


class PurchaseOrderLinkagePortal:
    """
    Context for the PO Linkage Portal.
    
    Provides methods to:
    - Get PO lines with their demand linkages
    - Find unlinked demands matching a PO line's part
    - Create/delete linkages
    """
    
    def __init__(self, purchase_order_id: int):
        self.purchase_order_id = purchase_order_id
        self._po = None
        
    @property
    def purchase_order(self) -> PurchaseOrderHeader:
        if self._po is None:
            self._po = PurchaseOrderHeader.query.get_or_404(self.purchase_order_id)
        return self._po
    
    def get_po_lines_with_demands(self) -> list[POLineWithDemands]:
        """
        Get all PO lines for this PO, with:
        - Already linked demands
        - Available unlinked demands (matching part_id)
        - Allocation calculations
        """
        result = []
        
        for line in self.purchase_order.purchase_order_lines:
            # Get existing links
            links = PartDemandPurchaseOrderLink.query.filter_by(
                purchase_order_line_id=line.id
            ).options(
                joinedload(PartDemandPurchaseOrderLink.part_demand)
                .joinedload(PartDemand.action)
                .joinedload(Action.maintenance_action_set)
            ).all()
            
            linked_demands = [link.part_demand for link in links if link.part_demand]
            
            # Calculate allocated quantity
            quantity_allocated = sum(link.quantity_allocated for link in links)
            quantity_available = line.quantity_ordered - quantity_allocated
            
            # Calculate allocation percentage
            if line.quantity_ordered > 0:
                allocation_pct = (quantity_allocated / line.quantity_ordered) * 100.0
            else:
                allocation_pct = 0.0
            
            # Find unlinked demands matching this part
            # Exclude demands already linked to any PO line
            linked_demand_ids = [d.id for d in linked_demands]
            
            all_linked_demand_ids = (
                db.session.query(PartDemandPurchaseOrderLink.part_demand_id)
                .distinct()
                .all()
            )
            all_linked_demand_ids = {row[0] for row in all_linked_demand_ids}
            
            linkable_demands = PartDemand.query.filter(
                PartDemand.part_id == line.part_id,
                PartDemand.id.not_in(all_linked_demand_ids) if all_linked_demand_ids else True
            ).options(
                joinedload(PartDemand.action).joinedload(Action.maintenance_action_set)
            ).order_by(PartDemand.priority.desc(), PartDemand.id).all()
            
            result.append(POLineWithDemands(
                po_line=line,
                linked_demands=linked_demands,
                linkable_demands=linkable_demands,
                quantity_available=quantity_available,
                allocation_percentage=allocation_pct
            ))
        
        return result
    
    def get_maintenance_events_with_demands(
        self,
        part_id: int | None = None,
        asset_id: int | None = None,
        make: str | None = None,
        model: str | None = None,
        asset_type_id: int | None = None,
        major_location_id: int | None = None,
        created_from: object | None = None,
        created_to: object | None = None,
        assigned_user_id: int | None = None,
    ) -> list[dict]:
        """
        Get maintenance events that have unlinked part demands.
        Optionally filter by part_id.
        """
        # Get all linked demand IDs
        all_linked_demand_ids = (
            db.session.query(PartDemandPurchaseOrderLink.part_demand_id)
            .distinct()
            .all()
        )
        all_linked_demand_ids = {row[0] for row in all_linked_demand_ids}
        
        # Query unlinked demands (we filter + then group into events)
        query = PartDemand.query.filter(
            PartDemand.id.not_in(all_linked_demand_ids) if all_linked_demand_ids else True
        )
        
        if part_id:
            query = query.filter(PartDemand.part_id == part_id)
        
        unlinked_demands = query.options(
            joinedload(PartDemand.action)
            .joinedload(Action.maintenance_action_set)
            .joinedload(MaintenanceActionSet.asset)
            .joinedload(Asset.make_model),
            joinedload(PartDemand.action)
            .joinedload(Action.maintenance_action_set)
            .joinedload(MaintenanceActionSet.asset)
            .joinedload(Asset.asset_type),
            joinedload(PartDemand.action)
            .joinedload(Action.maintenance_action_set)
            .joinedload(MaintenanceActionSet.asset)
            .joinedload(Asset.major_location),
        ).all()
        
        # Group by maintenance event
        events_dict = {}
        for demand in unlinked_demands:
            if not demand.action or not demand.action.maintenance_action_set:
                continue
                
            mas = demand.action.maintenance_action_set

            # Apply filters at the MAS / Asset level (keeps behavior simple and safe)
            if asset_id and mas.asset_id != asset_id:
                continue
            if assigned_user_id and mas.assigned_user_id != assigned_user_id:
                continue
            if created_from and getattr(mas, "created_at", None) and mas.created_at < created_from:
                continue
            if created_to and getattr(mas, "created_at", None) and mas.created_at > created_to:
                continue

            asset = mas.asset
            if major_location_id:
                if not asset or asset.major_location_id != major_location_id:
                    continue
            if asset_type_id:
                if not asset or asset.asset_type_id != asset_type_id:
                    continue
            if make:
                make_l = make.strip().lower()
                if make_l:
                    if not asset or not asset.make_model or make_l not in (asset.make_model.make or "").lower():
                        continue
            if model:
                model_l = model.strip().lower()
                if model_l:
                    if not asset or not asset.make_model or model_l not in (asset.make_model.model or "").lower():
                        continue

            event_id = mas.event_id
            
            if event_id not in events_dict:
                events_dict[event_id] = {
                    "event_id": event_id,
                    "maintenance_action_set": mas,
                    "demands": []
                }
            
            events_dict[event_id]["demands"].append(demand)
        
        return list(events_dict.values())
    
    def link_demand(self, po_line_id: int, part_demand_id: int, user_id: int) -> tuple[bool, str]:
        """
        Link a part demand to a PO line.
        
        Returns:
            (success: bool, message: str)
        """
        # Validate PO line belongs to this PO
        po_line = PurchaseOrderLine.query.get(po_line_id)
        if not po_line or po_line.purchase_order_id != self.purchase_order_id:
            return False, "Invalid PO line"
        
        # Get demand
        demand = PartDemand.query.get(part_demand_id)
        if not demand:
            return False, "Part demand not found"
        
        # Validate part IDs match
        if po_line.part_id != demand.part_id:
            return False, "Part ID mismatch: PO line and demand must have the same part"
        
        # Check if already linked
        existing_link = PartDemandPurchaseOrderLink.query.filter_by(
            purchase_order_line_id=po_line_id,
            part_demand_id=part_demand_id
        ).first()
        
        if existing_link:
            return False, "Demand is already linked to this PO line"
        
        # Check availability
        links = PartDemandPurchaseOrderLink.query.filter_by(
            purchase_order_line_id=po_line_id
        ).all()
        quantity_allocated = sum(link.quantity_allocated for link in links)
        quantity_available = po_line.quantity_ordered - quantity_allocated
        
        if demand.quantity_required > quantity_available:
            return False, f"Insufficient quantity available. Need {demand.quantity_required}, only {quantity_available} available"
        
        # Create link
        link = PartDemandPurchaseOrderLink(
            purchase_order_line_id=po_line_id,
            part_demand_id=part_demand_id,
            quantity_allocated=demand.quantity_required,
            created_by_id=user_id
        )
        
        db.session.add(link)
        
        try:
            db.session.commit()
            logger.info(f"Linked demand {part_demand_id} to PO line {po_line_id} by user {user_id}")
            return True, "Successfully linked demand to PO line"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to link demand {part_demand_id} to PO line {po_line_id}: {e}")
            return False, f"Database error: {str(e)}"
    
    def unlink_demand(self, part_demand_id: int) -> tuple[bool, str]:
        """
        Unlink a part demand from its PO line.
        
        Returns:
            (success: bool, message: str)
        """
        # Find the link
        link = PartDemandPurchaseOrderLink.query.filter_by(
            part_demand_id=part_demand_id
        ).first()
        
        if not link:
            return False, "No link found for this demand"
        
        # Validate PO line belongs to this PO
        po_line = PurchaseOrderLine.query.get(link.purchase_order_line_id)
        if not po_line or po_line.purchase_order_id != self.purchase_order_id:
            return False, "Link does not belong to this PO"
        
        db.session.delete(link)
        
        try:
            db.session.commit()
            logger.info(f"Unlinked demand {part_demand_id} from PO line {link.purchase_order_line_id}")
            return True, "Successfully unlinked demand"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to unlink demand {part_demand_id}: {e}")
            return False, f"Database error: {str(e)}"

