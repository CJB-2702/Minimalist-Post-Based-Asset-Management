from __future__ import annotations

from dataclasses import dataclass

from app import db
from app.data.inventory.purchasing.part_demand_link import PartDemandPurchaseOrderLink
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.data.maintenance.base.part_demands import PartDemand
from app.logger import get_logger

logger = get_logger("asset_management.buisness.inventory.purchasing.link_manager")


@dataclass(frozen=True)
class BrokenPurchaseOrderLink:
    link_id: int
    purchase_order_line_id: int | None
    part_demand_id: int | None
    reason: str


class PurchaseOrderLinkManager:
    """
    Link integrity tools for PO line <-> PartDemand links.
    """

    def detect_broken_links(self) -> list[BrokenPurchaseOrderLink]:
        broken: list[BrokenPurchaseOrderLink] = []
        for link in PartDemandPurchaseOrderLink.query.all():
            po_line = PurchaseOrderLine.query.get(link.purchase_order_line_id)
            demand = PartDemand.query.get(link.part_demand_id)
            if po_line is None:
                broken.append(
                    BrokenPurchaseOrderLink(
                        link_id=link.id,
                        purchase_order_line_id=link.purchase_order_line_id,
                        part_demand_id=link.part_demand_id,
                        reason="purchase_order_line_missing",
                    )
                )
            if demand is None:
                broken.append(
                    BrokenPurchaseOrderLink(
                        link_id=link.id,
                        purchase_order_line_id=link.purchase_order_line_id,
                        part_demand_id=link.part_demand_id,
                        reason="part_demand_missing",
                    )
                )
        return broken

    def link_demand(self, purchase_order_id: int, po_line_id: int, part_demand_id: int, user_id: int) -> tuple[bool, str]:
        """
        Link a part demand to a PO line.
        
        Args:
            purchase_order_id: ID of the purchase order (for validation)
            po_line_id: ID of the purchase order line
            part_demand_id: ID of the part demand to link
            user_id: ID of the user creating the link
        
        Returns:
            (success: bool, message: str)
        """
        # Validate PO line belongs to this PO
        po_line = PurchaseOrderLine.query.get(po_line_id)
        if not po_line or po_line.purchase_order_id != purchase_order_id:
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

    def unlink_demand(self, purchase_order_id: int, part_demand_id: int) -> tuple[bool, str]:
        """
        Unlink a part demand from its PO line.
        
        Args:
            purchase_order_id: ID of the purchase order (for validation)
            part_demand_id: ID of the part demand to unlink
        
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
        if not po_line or po_line.purchase_order_id != purchase_order_id:
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


