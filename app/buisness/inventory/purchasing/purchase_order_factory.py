from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import uuid4

from app import db
from app.buisness.inventory.shared.status_manager import InventoryStatusManager
from app.buisness.inventory.purchasing.purchase_order_context import PurchaseOrderContext
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.data.core.major_location import MajorLocation
from app.data.core.supply.part_definition import PartDefinition
from app.data.inventory.purchasing.part_demand_link import PartDemandPurchaseOrderLink
from app.data.inventory.purchasing.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.data.maintenance.base.part_demands import PartDemand
from app.logger import get_logger

logger = get_logger("asset_management.buisness.inventory.purchasing.factory")


class PurchaseOrderFactory:
    """
    Creates purchase orders and their linkages to part demands.

    This implements the lifecycle requirement:
    - creating a PO from part demands links PO lines <-> demand lines
    - setting PO/line statuses propagates to demand statuses
    """

    def __init__(self, status_manager: InventoryStatusManager | None = None):
        self.status_manager = status_manager or InventoryStatusManager()

    @staticmethod
    def _generate_po_number() -> str:
        # clarity > brevity: generate a stable, unique, human-readable identifier
        return f"PO-{date.today().isoformat()}-{uuid4().hex[:8].upper()}"

    @staticmethod
    def _recalculate_part_demand_quantity_on_order(part_demand_id: int) -> None:
        """
        Recalculate and update quantity_on_order for a part demand.
        
        This sums all quantity_allocated from all purchase order links for this demand.
        
        Args:
            part_demand_id: ID of the part demand to update
        """
        links = PartDemandPurchaseOrderLink.query.filter_by(
            part_demand_id=part_demand_id
        ).all()
        total_allocated = sum(link.quantity_allocated for link in links)
        
        demand = PartDemand.query.get(part_demand_id)
        if demand:
            demand.quantity_on_order = total_allocated if total_allocated > 0 else None
            logger.debug(f"Updated quantity_on_order for demand {part_demand_id}: {total_allocated}")

    @staticmethod
    def _validate_line_item(line_item: dict, line_number: int) -> tuple[int, float, float]:
        """
        Validate and extract line item data from dictionary.
        
        Args:
            line_item: Dictionary containing line item data with keys:
                - part_id (required)
                - quantity (required)
                - unit_cost (required)
                - confirmed (required, must be True)
            line_number: Line number for error messages
            
        Returns:
            Tuple of (part_id, quantity, unit_cost)
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        part_id = line_item.get('part_id')
        if not part_id:
            raise ValueError(f"part_id is required for line_item {line_number}")
        
        quantity = line_item.get('quantity')
        if quantity is None:
            raise ValueError(f"quantity is required for line_item {line_number}")
        
        unit_cost = line_item.get('unit_cost')
        if unit_cost is None:
            raise ValueError(f"unit_cost is required for line_item {line_number}")
        
        # Workflow-specific validation: price confirmation required
        confirmed = line_item.get('confirmed', False)
        if not confirmed:
            raise ValueError(f"Price confirmation is required for line_item {line_number}")
        
        return (part_id, float(quantity), float(unit_cost))

    @staticmethod
    def create_header(
        vendor_name: str,
        location_id: int,
        created_by_id: int,
        *,
        vendor_contact: str | None = None,
        storeroom_id: int | None = None,
        expected_delivery_date: date | None = None,
        shipping_cost: float = 0.0,
        tax_amount: float = 0.0,
        other_amount: float = 0.0,
        notes: str | None = None,
        status: str = "Draft",
    ) -> PurchaseOrderHeader:
        """
        Create a purchase order header.
        
        Args:
            vendor_name: Name of the vendor
            location_id: Major location ID
            created_by_id: User ID for audit fields
            vendor_contact: Optional vendor contact information
            storeroom_id: Optional storeroom ID
            expected_delivery_date: Optional expected delivery date
            shipping_cost: Shipping cost (defaults to 0.0)
            tax_amount: Tax amount (defaults to 0.0)
            other_amount: Other fees/charges (defaults to 0.0)
            notes: Optional notes
            status: Initial status (defaults to "Draft")
            
        Returns:
            PurchaseOrderHeader instance (added to session, not flushed)
        """
        if not vendor_name or not vendor_name.strip():
            raise ValueError("vendor_name is required")
        
        if not location_id:
            raise ValueError("location_id is required")
        
        po = PurchaseOrderHeader(
            po_number=PurchaseOrderFactory._generate_po_number(),
            vendor_name=vendor_name.strip(),
            vendor_contact=vendor_contact.strip() if vendor_contact else None,
            order_date=date.today(),
            expected_delivery_date=expected_delivery_date,
            status=status,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            other_amount=other_amount,
            notes=notes,
            major_location_id=location_id,
            storeroom_id=storeroom_id,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(po)
        logger.info(f"Created PO header - PO Number: {po.po_number}, Vendor: {vendor_name}")
        return po

    @staticmethod
    def add_line(
        purchase_order_id: int,
        part_id: int,
        quantity: float,
        unit_cost: float,
        created_by_id: int,
        *,
        line_number: int | None = None,
        expected_delivery_date: date | None = None,
        notes: str | None = None,
        status: str = "Pending",
    ) -> PurchaseOrderLine:
        """
        Add a line to an existing purchase order.
        
        Args:
            purchase_order_id: ID of the purchase order
            part_id: Part ID for the line
            quantity: Quantity to order
            unit_cost: Unit cost
            created_by_id: User ID for audit fields
            line_number: Optional line number (auto-assigned if not provided)
            expected_delivery_date: Optional expected delivery date
            notes: Optional notes
            status: Initial status (defaults to "Pending")
            
        Returns:
            PurchaseOrderLine instance (added to session, not flushed)
            
        Raises:
            ValueError: If purchase order not found, part not found, or invalid parameters
        """
        # Verify purchase order exists
        po = PurchaseOrderHeader.query.get(purchase_order_id)
        if not po:
            raise ValueError(f"Purchase order {purchase_order_id} not found")
        
        # Verify part exists
        part = PartDefinition.query.get(part_id)
        if not part:
            raise ValueError(f"Part with ID {part_id} not found")
        
        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        
        if unit_cost < 0:
            raise ValueError("unit_cost cannot be negative")
        
        # Auto-assign line number if not provided
        if line_number is None:
            existing_lines = po.purchase_order_lines.order_by(PurchaseOrderLine.line_number.desc()).first()
            line_number = (existing_lines.line_number + 1) if existing_lines else 1
        
        line = PurchaseOrderLine(
            purchase_order_id=purchase_order_id,
            part_id=part_id,
            quantity_ordered=float(quantity),
            unit_cost=float(unit_cost),
            line_number=line_number,
            expected_delivery_date=expected_delivery_date,
            notes=notes,
            status=status,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(line)
        logger.debug(f"Added PO line {line_number} to PO {purchase_order_id}: Part {part_id}, Qty {quantity}, Cost {unit_cost}")
        return line

    @staticmethod
    def add_link_to_line(
        purchase_order_line_id: int,
        part_demand_id: int,
        quantity_allocated: float,
        created_by_id: int,
        *,
        notes: str | None = None,
    ) -> PartDemandPurchaseOrderLink:
        """
        Add a link between a part demand and a purchase order line.
        
        Args:
            purchase_order_line_id: ID of the purchase order line
            part_demand_id: ID of the part demand
            quantity_allocated: Quantity allocated from the demand to the line
            created_by_id: User ID for audit fields
            notes: Optional notes
            
        Returns:
            PartDemandPurchaseOrderLink instance (added to session, not flushed)
            
        Raises:
            ValueError: If line or demand not found, part IDs don't match, or invalid parameters
        """
        # Verify purchase order line exists
        line = PurchaseOrderLine.query.get(purchase_order_line_id)
        if not line:
            raise ValueError(f"Purchase order line {purchase_order_line_id} not found")
        
        # Verify part demand exists
        demand = PartDemand.query.get(part_demand_id)
        if not demand:
            raise ValueError(f"Part demand {part_demand_id} not found")
        
        # Validate part ID matches
        if demand.part_id != line.part_id:
            raise ValueError(
                f"Part ID mismatch: demand {part_demand_id} has part_id {demand.part_id}, "
                f"but line has part_id {line.part_id}"
            )
        
        if quantity_allocated <= 0:
            raise ValueError("quantity_allocated must be > 0")
        
        # Validate status: do not allow already processed demands
        blocked_statuses = {"Issued", "Installed"}
        if demand.status in blocked_statuses:
            raise ValueError(
                f"Part demand {part_demand_id} is in status '{demand.status}' and cannot be linked"
            )
        
        # Check if link already exists
        existing_link = PartDemandPurchaseOrderLink.query.filter_by(
            purchase_order_line_id=purchase_order_line_id,
            part_demand_id=part_demand_id
        ).first()
        if existing_link:
            raise ValueError(
                f"Link already exists between purchase order line {purchase_order_line_id} "
                f"and part demand {part_demand_id}"
            )
        
        # Create link
        link = PartDemandPurchaseOrderLink(
            part_demand_id=part_demand_id,
            purchase_order_line_id=purchase_order_line_id,
            quantity_allocated=float(quantity_allocated),
            notes=notes,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(link)
        
        # Update demand status to Ordered if not already Issued/Installed
        if demand.status not in ("Issued", "Installed"):
            demand.status = "Ordered"
        
        # Recalculate and update quantity_on_order for the part demand
        PurchaseOrderFactory._recalculate_part_demand_quantity_on_order(part_demand_id)
        
        logger.debug(
            f"Linked demand {part_demand_id} to PO line {purchase_order_line_id}, "
            f"quantity_allocated: {quantity_allocated}"
        )
        return link

    @staticmethod
    def update_header(
        purchase_order_id: int,
        updated_by_id: int,
        *,
        vendor_name: str | None = None,
        vendor_contact: str | None = None,
        location_id: int | None = None,
        storeroom_id: int | None = None,
        expected_delivery_date: date | None = None,
        shipping_cost: float | None = None,
        tax_amount: float | None = None,
        other_amount: float | None = None,
        notes: str | None = None,
        status: str | None = None,
    ) -> PurchaseOrderHeader:
        """
        Update a purchase order header.
        
        Args:
            purchase_order_id: ID of the purchase order to update
            updated_by_id: User ID for audit fields
            vendor_name: Optional new vendor name
            vendor_contact: Optional new vendor contact
            location_id: Optional new major location ID
            storeroom_id: Optional new storeroom ID
            expected_delivery_date: Optional new expected delivery date
            shipping_cost: Optional new shipping cost
            tax_amount: Optional new tax amount
            other_amount: Optional new other amount
            notes: Optional new notes
            status: Optional new status
            
        Returns:
            PurchaseOrderHeader instance (updated, not flushed)
            
        Raises:
            ValueError: If purchase order not found or invalid parameters
        """
        po = PurchaseOrderHeader.query.get(purchase_order_id)
        if not po:
            raise ValueError(f"Purchase order {purchase_order_id} not found")
        
        # Update fields if provided
        if vendor_name is not None:
            if not vendor_name.strip():
                raise ValueError("vendor_name cannot be empty")
            po.vendor_name = vendor_name.strip()
        
        if vendor_contact is not None:
            po.vendor_contact = vendor_contact.strip() if vendor_contact else None
        
        if location_id is not None:
            po.major_location_id = location_id
        
        if storeroom_id is not None:
            po.storeroom_id = storeroom_id
        
        if expected_delivery_date is not None:
            po.expected_delivery_date = expected_delivery_date
        
        if shipping_cost is not None:
            po.shipping_cost = shipping_cost
        
        if tax_amount is not None:
            po.tax_amount = tax_amount
        
        if other_amount is not None:
            po.other_amount = other_amount
        
        if notes is not None:
            po.notes = notes
        
        if status is not None:
            po.status = status
        
        po.updated_by_id = updated_by_id
        
        logger.info(f"Updated PO header {purchase_order_id} ({po.po_number})")
        return po

    @staticmethod
    def recalculate_header_quantities(
        purchase_order_id: int,
        updated_by_id: int,
    ) -> PurchaseOrderHeader:
        """
        Recalculate all quantities and totals on the purchase order header.
        
        This function scans all lines and:
        - Recalculates total_cost (subtotal + shipping + tax + other)
        - Updates the header's updated_by_id
        
        Args:
            purchase_order_id: ID of the purchase order to update
            updated_by_id: User ID for audit fields
            
        Returns:
            PurchaseOrderHeader instance (updated, not flushed)
            
        Raises:
            ValueError: If purchase order not found
        """
        po = PurchaseOrderHeader.query.get(purchase_order_id)
        if not po:
            raise ValueError(f"Purchase order {purchase_order_id} not found")
        
        # Recalculate total using PurchaseOrderContext
        po_context = PurchaseOrderContext(purchase_order_id)
        po_context.calculate_total()
        
        # Update audit field
        po.updated_by_id = updated_by_id
        
        logger.info(
            f"Recalculated quantities for PO {purchase_order_id} ({po.po_number}): "
            f"total_cost={po.total_cost}"
        )
        return po


    @staticmethod
    def from_dict(
        po_data: dict,
        created_by_id: int,
    ) -> PurchaseOrderContext:
        """
        Create a purchase order from a dictionary.
        
        This is a simplified factory method that creates a PO from the JSON structure
        submitted by the create PO from part demands portal.
        
        Uses the primitive functions (create_header, add_line, add_link_to_line) to build the PO.
        
        Args:
            po_data: Dictionary containing purchase order data with keys:
                - header (required): Dictionary with:
                    - vendor_name (required)
                    - vendor_contact (optional)
                    - location_id (required)
                    - storeroom_id (optional)
                    - shipping_cost (optional, defaults to 0.0)
                    - tax_amount (optional, defaults to 0.0)
                    - other_amount (optional, defaults to 0.0)
                    - notes (optional)
                    - expected_delivery_date (optional, string '%Y-%m-%d' or date object)
                - line_items (required): List of dictionaries with:
                    - part_id (required)
                    - quantity (required)
                    - unit_cost (required)
                    - confirmed (required, must be True)
                    - linked_demands (optional, defaults to []): List of dictionaries with:
                        - part_demand_id (required)
                        - quantity_allocated (required)
                    - unlinked_quantity (optional, for tracking but not used in creation)
            created_by_id: User ID for audit fields
            
        Returns:
            PurchaseOrderContext instance
            
        Raises:
            ValueError: If required fields missing or invalid
        """
        # Extract and validate header data
        header = po_data.get('header')
        if not header:
            raise ValueError("header is required in po_data")
        
        vendor_name = (header.get('vendor_name') or '').strip()
        location_id = header.get('location_id')
        storeroom_id = header.get('storeroom_id')
        
        # Parse expected_delivery_date if provided
        expected_delivery_date = None
        if header.get('expected_delivery_date'):
            try:
                if isinstance(header['expected_delivery_date'], str):
                    expected_delivery_date = datetime.strptime(
                        header['expected_delivery_date'], 
                        '%Y-%m-%d'
                    ).date()
                else:
                    expected_delivery_date = header['expected_delivery_date']
            except (ValueError, TypeError):
                raise ValueError(f"Invalid expected_delivery_date format: {header['expected_delivery_date']}")
        
        # Create purchase order header using primitive function
        po = PurchaseOrderFactory.create_header(
            vendor_name=vendor_name,
            location_id=location_id,
            created_by_id=created_by_id,
            vendor_contact=header.get('vendor_contact'),
            storeroom_id=storeroom_id,
            expected_delivery_date=expected_delivery_date,
            shipping_cost=header.get('shipping_cost') or 0.0,
            tax_amount=header.get('tax_amount') or 0.0,
            other_amount=header.get('other_amount') or 0.0,
            notes=header.get('notes'),
            status="Ordered",
        )
        db.session.flush()  # Flush to get PO ID
        
        # Process line items
        line_items = po_data.get('line_items', [])
        if not line_items:
            raise ValueError("At least one line_item is required")
        
        line_number = 1
        all_part_demand_ids = set()
        
        for line_item in line_items:
            # Validate and extract line item data
            part_id, quantity, unit_cost = PurchaseOrderFactory._validate_line_item(
                line_item, line_number
            )
            
            # Create purchase order line using primitive function
            # Validation is handled in add_line (part exists, quantity > 0, unit_cost >= 0)
            line = PurchaseOrderFactory.add_line(
                purchase_order_id=po.id,
                part_id=part_id,
                quantity=quantity,
                unit_cost=unit_cost,
                created_by_id=created_by_id,
                line_number=line_number,
                status="Ordered",
            )
            db.session.flush()  # Flush to get line ID
            
            # Process linked demands using primitive function
            # Validation is handled in add_link_to_line (demand exists, part ID matches, etc.)
            linked_demands = line_item.get('linked_demands', [])
            for linked_demand in linked_demands:
                part_demand_id = linked_demand.get('part_demand_id')
                if not part_demand_id:
                    raise ValueError(f"part_demand_id is required in linked_demand for line_item {line_number}")
                
                quantity_allocated = linked_demand.get('quantity_allocated')
                if quantity_allocated is None:
                    raise ValueError(f"quantity_allocated is required in linked_demand for part_demand_id {part_demand_id}")
                
                # Create link using primitive function
                # This will update demand status and quantity_on_order automatically
                PurchaseOrderFactory.add_link_to_line(
                    purchase_order_line_id=line.id,
                    part_demand_id=part_demand_id,
                    quantity_allocated=float(quantity_allocated),
                    created_by_id=created_by_id,
                )
                all_part_demand_ids.add(part_demand_id)
            
            line_number += 1
        
        # Note: quantity_on_order recalculation is already handled by add_link_to_line,
        # but we ensure it's up-to-date for all demands
        for part_demand_id in all_part_demand_ids:
            PurchaseOrderFactory._recalculate_part_demand_quantity_on_order(part_demand_id)
        
        # PO status propagation (also sets linked lines/demands consistently)
        factory = PurchaseOrderFactory()
        factory.status_manager.propagate_purchase_order_status(po.id, "Ordered")
        
        # Calculate total
        po_context = PurchaseOrderContext(po.id)
        po_context.calculate_total()
        db.session.flush()
        
        # Log final PO state
        logger.info(
            f"PO {po.id} ({po.po_number}) created with {line_number - 1} lines, "
            f"linked to {len(all_part_demand_ids)} part demands, status: {po.status}"
        )
        
        return po_context

    

    @staticmethod
    def create_from_existing_po(
        source_po_id: int,
        header_info: dict,
        created_by_id: int
    ) -> PurchaseOrderContext:
        """
        Create a purchase order by copying from an existing purchase order.
        
        Args:
            source_po_id: ID of the purchase order to copy from
            header_info: Dictionary with header information (can override source PO):
                - vendor_name (optional, uses source if not provided)
                - vendor_contact (optional)
                - shipping_cost (optional)
                - tax_amount (optional)
                - notes (optional)
                - location_id (optional, major_location_id)
                - expected_delivery_date (optional, date object)
            created_by_id: User ID for audit fields
            
        Returns:
            PurchaseOrderContext instance
            
        Raises:
            ValueError: If source PO not found
        """
        # Get source PO
        source_po = PurchaseOrderHeader.query.get(source_po_id)
        if not source_po:
            raise ValueError(f"Source purchase order {source_po_id} not found")
        
        # Extract header info (use source PO values as defaults)
        vendor_name = header_info.get('vendor_name', source_po.vendor_name)
        major_location_id = header_info.get('location_id', source_po.major_location_id)
        storeroom_id = header_info.get('storeroom_id', source_po.storeroom_id)
        
        # Create new PO header using primitive function
        # Validation is handled in create_header (vendor_name, location_id)
        shipping_cost = header_info.get('shipping_cost')
        if shipping_cost is None:
            shipping_cost = source_po.shipping_cost if source_po.shipping_cost is not None else 0.0
        
        tax_amount = header_info.get('tax_amount')
        if tax_amount is None:
            tax_amount = source_po.tax_amount if source_po.tax_amount is not None else 0.0
        
        other_amount = header_info.get('other_amount')
        if other_amount is None:
            other_amount = source_po.other_amount if source_po.other_amount is not None else 0.0
        
        po = PurchaseOrderFactory.create_header(
            vendor_name=vendor_name,
            location_id=major_location_id,
            created_by_id=created_by_id,
            vendor_contact=header_info.get('vendor_contact', source_po.vendor_contact),
            storeroom_id=storeroom_id,
            expected_delivery_date=header_info.get('expected_delivery_date', source_po.expected_delivery_date),
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            other_amount=other_amount,
            notes=header_info.get('notes', source_po.notes),
            status='Draft',  # New PO starts as Draft
        )
        db.session.flush()  # Flush to get PO ID
        
        # Copy lines from source PO using primitive function
        # Validation is handled in add_line (part exists, quantity > 0, unit_cost >= 0)
        line_number = 1
        for source_line in source_po.purchase_order_lines:
            PurchaseOrderFactory.add_line(
                purchase_order_id=po.id,
                part_id=source_line.part_id,
                quantity=source_line.quantity_ordered,
                unit_cost=source_line.unit_cost,
                created_by_id=created_by_id,
                line_number=line_number,
                expected_delivery_date=source_line.expected_delivery_date,
                notes=source_line.notes,
                status='Pending',  # New lines start as Pending
            )
            line_number += 1
        
        db.session.flush()
        
        # Calculate total
        po_context = PurchaseOrderContext(po.id)
        po_context.calculate_total()
        db.session.flush()
        
        return po_context


