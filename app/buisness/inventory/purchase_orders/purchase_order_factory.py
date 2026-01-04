from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import uuid4

from app import db
from app.buisness.inventory.status.status_manager import InventoryStatusManager
from app.buisness.inventory.purchase_orders.purchase_order_context import PurchaseOrderContext
from app.buisness.maintenance.base.maintenance_context import MaintenanceContext
from app.data.core.major_location import MajorLocation
from app.data.core.supply.part_definition import PartDefinition
from app.data.inventory.ordering.part_demand_purchase_order_line import PartDemandPurchaseOrderLink
from app.data.inventory.ordering.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine
from app.data.maintenance.base.part_demands import PartDemand
from app.logger import get_logger

logger = get_logger("asset_management.buisness.inventory.purchase_orders.factory")


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

    def create_from_part_demands(
        self,
        *,
        vendor_name: str,
        major_location_id: int | None,
        storeroom_id: int | None,
        part_demand_ids: list[int],
        unit_cost_by_part_demand_id: dict[int, float],
        created_by_id: int,
    ) -> PurchaseOrderHeader:
        demands = PartDemand.query.filter(PartDemand.id.in_(part_demand_ids)).all()
        if len(demands) != len(part_demand_ids):
            raise ValueError("One or more part demands not found")

        po = PurchaseOrderHeader(
            po_number=self._generate_po_number(),
            vendor_name=vendor_name,
            order_date=date.today(),
            status="Ordered",
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(po)
        db.session.flush()
        logger.info(f"Created PO header - ID: {po.id}, PO Number: {po.po_number}, Vendor: {vendor_name}")

        # Create one PO line per demand (simple, explicit traceability)
        line_number = 1
        for demand in demands:
            unit_cost = unit_cost_by_part_demand_id.get(demand.id)
            if unit_cost is None:
                raise ValueError(f"Missing unit cost for part_demand_id={demand.id}")

            line = PurchaseOrderLine(
                purchase_order_id=po.id,
                part_id=demand.part_id,
                quantity_ordered=demand.quantity_required,
                quantity_accepted=0.0,
                quantity_rejected=0.0,
                unit_cost=unit_cost,
                line_number=line_number,
                status="Ordered",
                created_by_id=created_by_id,
                updated_by_id=created_by_id,
            )
            db.session.add(line)
            db.session.flush()

            link = PartDemandPurchaseOrderLink(
                part_demand_id=demand.id,
                purchase_order_line_id=line.id,
                quantity_allocated=demand.quantity_required,
                created_by_id=created_by_id,
                updated_by_id=created_by_id,
            )
            db.session.add(link)

            # Demand status becomes Ordered
            if demand.status not in ("Issued", "Installed"):
                demand.status = "Ordered"

            line_number += 1

        # PO status propagation (also sets linked lines/demands consistently)
        self.status_manager.propagate_purchase_order_status(po.id, "Ordered")
        
        # Log final PO state
        line_count = line_number - 1
        logger.info(f"PO {po.id} ({po.po_number}) created with {line_count} lines, status: {po.status}")
        # Query lines separately since purchase_order_lines is a dynamic relationship
        po_lines = PurchaseOrderLine.query.filter_by(purchase_order_id=po.id).all()
        for line in po_lines:
            logger.debug(f"  PO Line {line.line_number}: Part {line.part_id}, Qty {line.quantity_ordered}, Cost {line.unit_cost}, Status {line.status}")
        
        return po

    @staticmethod
    def create_from_part_demand_lines(
        *,
        header_info: dict,
        created_by_id: int,
        part_demand_ids: list[int],
        prices_by_part_id: dict[int, float],
    ) -> PurchaseOrderContext:
        """
        Create a purchase order from a selected set of part demand lines.

        Factory Pattern 2 (from parent lines):
        - user selects demand lines (potentially across multiple maintenance events)
        - PO lines are created per *part_id*, with quantity_ordered = sum(quantity_required) across selected demands
        - each demand is linked to the created PO line (quantity_allocated = demand.quantity_required)
        - user provides a single unit cost per part_id and must confirm it in the UI (enforced in routes)
        """
        vendor_name = (header_info.get("vendor_name") or "").strip()
        if not vendor_name:
            raise ValueError("vendor_name is required in header_info")

        major_location_id = header_info.get("location_id")
        if not major_location_id:
            raise ValueError("location_id is required in header_info")
        storeroom_id = header_info.get("storeroom_id")

        demands = PartDemand.query.filter(PartDemand.id.in_(part_demand_ids)).all()
        if len(demands) != len(part_demand_ids):
            raise ValueError("One or more part demands not found")

        # Validate statuses: do not allow already processed demands to be ordered again.
        blocked_statuses = {"Issued", "Ordered", "Installed"}
        for d in demands:
            if d.status in blocked_statuses:
                raise ValueError(f"Part demand {d.id} is in status '{d.status}' and cannot be ordered")

        # Group demands by part_id; qty is forced to sum of demand.quantity_required.
        by_part_id: dict[int, list[PartDemand]] = {}
        for d in demands:
            by_part_id.setdefault(d.part_id, []).append(d)

        po = PurchaseOrderHeader(
            po_number=PurchaseOrderFactory._generate_po_number(),
            vendor_name=vendor_name,
            order_date=date.today(),
            status="Ordered",
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(po)
        db.session.flush()

        # Apply optional header fields (match create_from_maintenance_event behavior)
        if header_info.get("vendor_contact"):
            po.vendor_contact = header_info["vendor_contact"]
        if header_info.get("shipping_cost") is not None:
            po.shipping_cost = header_info["shipping_cost"]
        if header_info.get("tax_amount") is not None:
            po.tax_amount = header_info["tax_amount"]
        if header_info.get("notes"):
            po.notes = header_info["notes"]
        if header_info.get("expected_delivery_date"):
            po.expected_delivery_date = header_info["expected_delivery_date"]

        line_number = 1
        for part_id, part_demands in sorted(by_part_id.items(), key=lambda x: x[0]):
            unit_cost = prices_by_part_id.get(part_id)
            if unit_cost is None:
                raise ValueError(f"Missing unit cost for part_id={part_id}")
            if unit_cost < 0:
                raise ValueError(f"Unit cost cannot be negative for part_id={part_id}")

            total_qty = float(sum(d.quantity_required or 0.0 for d in part_demands))
            if total_qty <= 0:
                raise ValueError(f"Total quantity must be > 0 for part_id={part_id}")

            line = PurchaseOrderLine(
                purchase_order_id=po.id,
                part_id=part_id,
                quantity_ordered=total_qty,
                quantity_accepted=0.0,
                quantity_rejected=0.0,
                unit_cost=float(unit_cost),
                line_number=line_number,
                status="Ordered",
                created_by_id=created_by_id,
                updated_by_id=created_by_id,
            )
            db.session.add(line)
            db.session.flush()

            for demand in part_demands:
                link = PartDemandPurchaseOrderLink(
                    part_demand_id=demand.id,
                    purchase_order_line_id=line.id,
                    quantity_allocated=float(demand.quantity_required or 0.0),
                    created_by_id=created_by_id,
                    updated_by_id=created_by_id,
                )
                db.session.add(link)

                if demand.status not in ("Issued", "Installed"):
                    demand.status = "Ordered"

            line_number += 1

        # PO status propagation (also sets linked lines/demands consistently)
        factory = PurchaseOrderFactory()
        factory.status_manager.propagate_purchase_order_status(po.id, "Ordered")

        return PurchaseOrderContext(po.id)

    @staticmethod
    def create_from_dict(
        po_data: dict,
        created_by_id: int,
        lookup_location_by_name: bool = False
    ) -> PurchaseOrderContext:
        """
        Create a purchase order from a dictionary.
        
        Args:
            po_data: Dictionary containing purchase order data with keys:
                - vendor_name (required)
                - vendor_contact (optional)
                - shipping_cost (optional)
                - tax_amount (optional)
                - notes (optional)
                - major_location_name (optional, used if lookup_location_by_name=True)
                - major_location_id (optional, used if lookup_location_by_name=False)
                - expected_delivery_date (optional, string in 'YYYY-MM-DD' format)
                - status (optional, defaults to 'Draft')
                - lines (required, list of dictionaries with keys:
                    - part_number (required)
                    - quantity_ordered (required)
                    - unit_cost (required)
                    - notes (optional)
            created_by_id: User ID for audit fields
            lookup_location_by_name: If True, look up major_location by name instead of using major_location_id
            
        Returns:
            PurchaseOrderContext instance
        """
        # Extract header data
        vendor_name = po_data.get('vendor_name')
        if not vendor_name:
            raise ValueError("vendor_name is required")
        
        # Handle major_location lookup
        major_location_id = None
        if lookup_location_by_name:
            major_location_name = po_data.get('major_location_name')
            if major_location_name:
                major_location = MajorLocation.query.filter_by(name=major_location_name).first()
                if not major_location:
                    raise ValueError(f"Major location '{major_location_name}' not found")
                major_location_id = major_location.id
        else:
            major_location_id = po_data.get('major_location_id')
        
        if not major_location_id:
            raise ValueError("location_id is required")
        
        # Parse expected_delivery_date if provided
        expected_delivery_date = None
        if po_data.get('expected_delivery_date'):
            try:
                expected_delivery_date = datetime.strptime(
                    po_data['expected_delivery_date'], 
                    '%Y-%m-%d'
                ).date()
            except ValueError:
                raise ValueError(f"Invalid expected_delivery_date format: {po_data['expected_delivery_date']}")
        
        # Create purchase order header
        po = PurchaseOrderHeader(
            po_number=PurchaseOrderFactory._generate_po_number(),
            vendor_name=vendor_name,
            vendor_contact=po_data.get('vendor_contact'),
            order_date=date.today(),
            expected_delivery_date=expected_delivery_date,
            status=po_data.get('status', 'Draft'),
            shipping_cost=po_data.get('shipping_cost'),
            tax_amount=po_data.get('tax_amount'),
            notes=po_data.get('notes'),
            major_location_id=major_location_id,
            storeroom_id=po_data.get('storeroom_id'),
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(po)
        db.session.flush()
        
        # Create purchase order lines
        lines_data = po_data.get('lines', [])
        line_number = 1
        for line_data in lines_data:
            part_number = line_data.get('part_number')
            if not part_number:
                raise ValueError(f"part_number is required for line {line_number}")
            
            # Look up part by part_number
            part = PartDefinition.query.filter_by(part_number=part_number).first()
            if not part:
                raise ValueError(f"Part with part_number '{part_number}' not found")
            
            quantity_ordered = line_data.get('quantity_ordered')
            if quantity_ordered is None:
                raise ValueError(f"quantity_ordered is required for line {line_number}")
            
            unit_cost = line_data.get('unit_cost')
            if unit_cost is None:
                raise ValueError(f"unit_cost is required for line {line_number}")
            
            # Create purchase order line
            line = PurchaseOrderLine(
                purchase_order_id=po.id,
                part_id=part.id,
                quantity_ordered=float(quantity_ordered),
                quantity_accepted=0.0,
                quantity_rejected=0.0,
                unit_cost=float(unit_cost),
                line_number=line_number,
                status=line_data.get('status', 'Pending'),
                notes=line_data.get('notes'),
                created_by_id=created_by_id,
                updated_by_id=created_by_id,
            )
            db.session.add(line)
            line_number += 1
        
        db.session.flush()
        
        # Return context
        return PurchaseOrderContext(po.id)

    @staticmethod
    def create_from_maintenance_event(
        maintenance_event_id: int,
        header_info: dict,
        created_by_id: int,
        part_demand_ids: list[int] | None = None,
        unit_cost_by_part_demand_id: dict[int, float] | None = None,
    ) -> PurchaseOrderContext:
        """
        Create a purchase order from a maintenance event's part demands.
        
        Args:
            maintenance_event_id: Event ID (maintenance event)
            header_info: Dictionary with header information:
                - vendor_name (required)
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
            ValueError: If event not found, no part demands exist, or required fields missing
        """
        logger.info(f"create_from_maintenance_event called - event_id: {maintenance_event_id}, created_by_id: {created_by_id}")
        logger.debug(f"header_info: {header_info}")
        
        # Get maintenance context from event
        try:
            logger.info(f"Attempting to get MaintenanceContext from event {maintenance_event_id}")
            maintenance_context = MaintenanceContext.from_event(maintenance_event_id)
            logger.info(f"Successfully retrieved MaintenanceContext for event {maintenance_event_id}")
        except ValueError as e:
            logger.error(f"Failed to get MaintenanceContext from event {maintenance_event_id}: {e}")
            raise ValueError(f"Maintenance event {maintenance_event_id} not found: {e}")
        
        # Get part demands from the maintenance event
        part_demands = maintenance_context.struct.part_demands
        logger.info(f"Found {len(part_demands)} total part demands for event {maintenance_event_id}")
        
        # Log all demand statuses
        demand_statuses = [d.status for d in part_demands]
        logger.debug(f"Part demand statuses: {demand_statuses}")
        
        # Filter to only include demands that can be ordered
        # Exclude demands that are already Ordered, Shipped, Arrived, At Inventory, Issued, or Installed
        orderable_statuses = {'Planned', 'Pending Manager Approval', 'Pending Inventory Approval'}
        orderable_demands = [d for d in part_demands if d.status in orderable_statuses]
        logger.info(f"Found {len(orderable_demands)} orderable part demands (statuses: {orderable_statuses})")
        
        # Optional: user-selected subset of demands (portal allows removing lines)
        if part_demand_ids is not None:
            selected_ids = set(int(did) for did in part_demand_ids)
            orderable_demands = [d for d in orderable_demands if d.id in selected_ids]
            logger.info(
                f"Filtered orderable demands to selected subset: {len(orderable_demands)} demands (selected_ids={sorted(selected_ids)})"
            )

        if not orderable_demands:
            logger.warning(f"No orderable part demands found for maintenance event {maintenance_event_id}. All demands have statuses: {set(demand_statuses)}")
            raise ValueError(f"No orderable part demands found for maintenance event {maintenance_event_id}")
        
        # Extract header info
        vendor_name = header_info.get('vendor_name')
        if not vendor_name:
            logger.error("vendor_name is missing from header_info")
            raise ValueError("vendor_name is required in header_info")
        
        major_location_id = header_info.get('location_id')
        if not major_location_id:
            raise ValueError("location_id is required in header_info")
        storeroom_id = header_info.get('storeroom_id')
        logger.info(f"Creating PO with vendor: {vendor_name}, location_id: {major_location_id}, storeroom_id: {storeroom_id}")
        
        # Build unit_cost_by_part_demand_id.
        #
        # Golden-path portal can pass explicit unit costs per demand. If not provided, fall back to
        # the part's last_unit_cost (or 0.0).
        unit_cost_by_part_demand_id_resolved: dict[int, float] = {}
        for demand in orderable_demands:
            if unit_cost_by_part_demand_id is not None and demand.id in unit_cost_by_part_demand_id:
                unit_cost_by_part_demand_id_resolved[demand.id] = float(unit_cost_by_part_demand_id[demand.id])
                continue

            part = PartDefinition.query.get(demand.part_id)
            if part and part.last_unit_cost:
                unit_cost_by_part_demand_id_resolved[demand.id] = float(part.last_unit_cost)
                logger.debug(
                    f"Using last_unit_cost {part.last_unit_cost} for part {part.part_number} (demand_id: {demand.id})"
                )
            else:
                unit_cost_by_part_demand_id_resolved[demand.id] = 0.0
                logger.warning(
                    f"No last_unit_cost for part_id {demand.part_id}, using 0.0 (demand_id: {demand.id})"
                )
        
        logger.info(f"Unit costs mapped for {len(unit_cost_by_part_demand_id_resolved)} demands")
        
        # Create factory instance
        factory = PurchaseOrderFactory()
        
        # Create PO from part demands
        resolved_part_demand_ids = [d.id for d in orderable_demands]
        logger.info(f"Creating PO from {len(resolved_part_demand_ids)} part demands: {resolved_part_demand_ids}")
        
        try:
            po = factory.create_from_part_demands(
                vendor_name=vendor_name,
                major_location_id=major_location_id,
                storeroom_id=storeroom_id,
                part_demand_ids=resolved_part_demand_ids,
                unit_cost_by_part_demand_id=unit_cost_by_part_demand_id_resolved,
                created_by_id=created_by_id,
            )
            logger.info(f"Successfully created PO header - PO ID: {po.id}, PO Number: {po.po_number}")
        except Exception as e:
            logger.error(f"Error in create_from_part_demands: {e}", exc_info=True)
            raise
        
        # Update PO with additional header info
        if header_info.get('vendor_contact'):
            po.vendor_contact = header_info['vendor_contact']
            logger.debug(f"Set vendor_contact: {po.vendor_contact}")
        if header_info.get('shipping_cost') is not None:
            po.shipping_cost = header_info['shipping_cost']
            logger.debug(f"Set shipping_cost: {po.shipping_cost}")
        if header_info.get('tax_amount') is not None:
            po.tax_amount = header_info['tax_amount']
            logger.debug(f"Set tax_amount: {po.tax_amount}")
        if header_info.get('notes'):
            po.notes = header_info['notes']
            logger.debug(f"Set notes: {po.notes}")
        if header_info.get('expected_delivery_date'):
            po.expected_delivery_date = header_info['expected_delivery_date']
            logger.debug(f"Set expected_delivery_date: {po.expected_delivery_date}")
        
        db.session.flush()
        logger.info(f"PO {po.id} flushed to database")
        
        # Create context
        context = PurchaseOrderContext(po.id)
        logger.info(f"Created PurchaseOrderContext for PO ID: {po.id}, context.purchase_order_id: {context.purchase_order_id}")
        
        return context

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
        if not vendor_name:
            raise ValueError("vendor_name is required")
        
        major_location_id = header_info.get('location_id', source_po.major_location_id)
        if not major_location_id:
            raise ValueError("location_id is required")
        storeroom_id = header_info.get('storeroom_id', source_po.storeroom_id)
        
        # Create new PO header
        po = PurchaseOrderHeader(
            po_number=PurchaseOrderFactory._generate_po_number(),
            vendor_name=vendor_name,
            vendor_contact=header_info.get('vendor_contact', source_po.vendor_contact),
            order_date=date.today(),
            expected_delivery_date=header_info.get('expected_delivery_date', source_po.expected_delivery_date),
            status='Draft',  # New PO starts as Draft
            shipping_cost=header_info.get('shipping_cost', source_po.shipping_cost),
            tax_amount=header_info.get('tax_amount', source_po.tax_amount),
            notes=header_info.get('notes', source_po.notes),
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(po)
        db.session.flush()
        
        # Copy lines from source PO
        line_number = 1
        for source_line in source_po.purchase_order_lines:
            line = PurchaseOrderLine(
                purchase_order_id=po.id,
                part_id=source_line.part_id,
                quantity_ordered=source_line.quantity_ordered,
                quantity_accepted=0.0,  # Reset quantities for new PO
                quantity_rejected=0.0,
                unit_cost=source_line.unit_cost,
                line_number=line_number,
                status='Pending',  # New lines start as Pending
                expected_delivery_date=source_line.expected_delivery_date,
                notes=source_line.notes,
                created_by_id=created_by_id,
                updated_by_id=created_by_id,
            )
            db.session.add(line)
            line_number += 1
        
        db.session.flush()
        
        return PurchaseOrderContext(po.id)

    @staticmethod
    def create_blank(
        header_info: dict,
        created_by_id: int
    ) -> PurchaseOrderContext:
        """
        Create a blank purchase order with no lines.
        
        Args:
            header_info: Dictionary with header information:
                - vendor_name (required)
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
            ValueError: If required fields missing
        """
        # Extract header info
        vendor_name = header_info.get('vendor_name')
        if not vendor_name:
            raise ValueError("vendor_name is required in header_info")
        
        major_location_id = header_info.get('location_id')
        if not major_location_id:
            raise ValueError("location_id is required in header_info")
        
        # Create blank PO
        po = PurchaseOrderHeader(
            po_number=PurchaseOrderFactory._generate_po_number(),
            vendor_name=vendor_name,
            vendor_contact=header_info.get('vendor_contact'),
            order_date=date.today(),
            expected_delivery_date=header_info.get('expected_delivery_date'),
            status='Draft',
            shipping_cost=header_info.get('shipping_cost'),
            tax_amount=header_info.get('tax_amount'),
            notes=header_info.get('notes'),
            major_location_id=major_location_id,
            storeroom_id=header_info.get('storeroom_id'),
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(po)
        db.session.flush()
        
        return PurchaseOrderContext(po.id)

    @staticmethod
    def create_unlinked(
        header_info: dict,
        po_lines: list[dict],
        created_by_id: int
    ) -> PurchaseOrderContext:
        """
        Create an unlinked purchase order from header info and self-defined lines.
        
        Factory Pattern 3 (unlinked from self lines):
        - User provides header information and a list of PO lines
        - No automatic links to part demands are created
        - Purchase order is created in Draft status
        
        Args:
            header_info: Dictionary with header information:
                - vendor_name (required)
                - vendor_contact (optional)
                - shipping_cost (optional)
                - tax_amount (optional)
                - notes (optional)
                - location_id (optional, major_location_id)
                - storeroom_id (optional)
                - expected_delivery_date (optional, date object)
            po_lines: List of dictionaries with line information:
                - part_id (required)
                - quantity_ordered (required)
                - unit_cost (required)
                - expected_delivery_date (optional, date object)
                - notes (optional)
            created_by_id: User ID for audit fields
            
        Returns:
            PurchaseOrderContext instance
            
        Raises:
            ValueError: If required fields missing or invalid
        """
        # Extract header info
        vendor_name = header_info.get('vendor_name')
        if not vendor_name:
            raise ValueError("vendor_name is required in header_info")
        
        major_location_id = header_info.get('location_id')
        if not major_location_id:
            raise ValueError("location_id is required in header_info")
        
        if not po_lines:
            raise ValueError("At least one PO line is required")
        
        # Create PO header
        po = PurchaseOrderHeader(
            po_number=PurchaseOrderFactory._generate_po_number(),
            vendor_name=vendor_name,
            vendor_contact=header_info.get('vendor_contact'),
            order_date=date.today(),
            expected_delivery_date=header_info.get('expected_delivery_date'),
            status='Draft',  # Unlinked POs start as Draft
            shipping_cost=header_info.get('shipping_cost') or 0.0,
            tax_amount=header_info.get('tax_amount') or 0.0,
            notes=header_info.get('notes'),
            major_location_id=major_location_id,
            storeroom_id=header_info.get('storeroom_id'),
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(po)
        db.session.flush()
        
        # Create PO lines
        line_number = 1
        for line_data in po_lines:
            part_id = line_data.get('part_id')
            if not part_id:
                raise ValueError(f"part_id is required for line {line_number}")
            
            # Verify part exists
            part = PartDefinition.query.get(part_id)
            if not part:
                raise ValueError(f"Part with ID {part_id} not found")
            
            quantity_ordered = line_data.get('quantity_ordered')
            if quantity_ordered is None or quantity_ordered <= 0:
                raise ValueError(f"quantity_ordered must be > 0 for line {line_number}")
            
            unit_cost = line_data.get('unit_cost')
            if unit_cost is None:
                raise ValueError(f"unit_cost is required for line {line_number}")
            if unit_cost < 0:
                raise ValueError(f"unit_cost cannot be negative for line {line_number}")
            
            # Create purchase order line
            line = PurchaseOrderLine(
                purchase_order_id=po.id,
                part_id=part_id,
                quantity_ordered=float(quantity_ordered),
                quantity_accepted=0.0,
                quantity_rejected=0.0,
                unit_cost=float(unit_cost),
                line_number=line_number,
                status='Draft',  # Lines start as Draft
                expected_delivery_date=line_data.get('expected_delivery_date'),
                notes=line_data.get('notes'),
                created_by_id=created_by_id,
                updated_by_id=created_by_id,
            )
            db.session.add(line)
            line_number += 1
        
        db.session.flush()
        
        # Create context and calculate total
        po_context = PurchaseOrderContext(po.id)
        po_context.calculate_total()
        db.session.flush()
        
        logger.info(f"Created unlinked PO {po.id} ({po.po_number}) with {line_number - 1} lines")
        
        return po_context


