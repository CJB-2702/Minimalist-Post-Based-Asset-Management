from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app import db
from app.buisness.inventory.arrivals.arrival_linkage_manager import ArrivalLinkageManager
from app.buisness.inventory.inventory.inventory_manager import InventoryManager
from app.data.inventory.arrivals.arrival_header import ArrivalHeader
from app.data.inventory.arrivals.arrival_line import ArrivalLine
from app.data.inventory.inventory.storeroom import Storeroom
from app.data.inventory.purchasing.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.purchasing.purchase_order_line import PurchaseOrderLine
from app.logger import get_logger
from app.services.inventory.arrivals.arrival_po_line_finder_service import ArrivalPOLineFinderService
from app.services.inventory.arrivals.arrival_po_line_selection_service import (
    ArrivalPOLineSelectionService,
)

logger = get_logger("asset_management.buisness.inventory.arrivals.factory")


@dataclass(frozen=True)
class ArrivalHeaderInput:
    package_number: str
    major_location_id: int
    storeroom_id: int
    tracking_number: str | None = None
    carrier: str | None = None
    notes: str | None = None


class ArrivalFactory:
    """
    Business factory for creating arrivals (package headers + part arrivals).

    Mirrors the PurchaseOrderFactory approach:
    - Centralize validation and creation decisions here
    - Keep session commit/rollback in the caller (routes/services)
    - Provide a single high-level workflow for "create arrival" portals
    """

    @staticmethod
    def _clean_optional_str(value: object) -> str | None:
        if value is None:
            return None
        s = str(value).strip()
        return s or None

    @staticmethod
    def _parse_header(arrival_data: dict) -> ArrivalHeaderInput:
        """
        Parse and validate arrival header data.
        
        Requires:
        - package_number (str, required)
        - major_location_id (int, required) - Major location where package is received
        - storeroom_id (int, required) - Storeroom where inventory will be stored
        
        Raises:
            ValueError: If any required field is missing or invalid
        """
        header = arrival_data.get("header") or {}

        package_number = (header.get("package_number") or "").strip()
        if not package_number:
            raise ValueError("Package number is required")

        major_location_id = header.get("major_location_id")
        if not major_location_id:
            raise ValueError("Major location is required")

        storeroom_id = header.get("storeroom_id")
        if not storeroom_id:
            raise ValueError("Storeroom is required")

        return ArrivalHeaderInput(
            package_number=package_number,
            major_location_id=int(major_location_id),
            storeroom_id=int(storeroom_id),
            tracking_number=ArrivalFactory._clean_optional_str(header.get("tracking_number")),
            carrier=ArrivalFactory._clean_optional_str(header.get("carrier")),
            notes=ArrivalFactory._clean_optional_str(header.get("notes")),
        )

    # -------------------------------------------------------------------------
    # Primitive building blocks
    # -------------------------------------------------------------------------

    @staticmethod
    def create_package_header(
        *,
        package_number: str,
        major_location_id: int,
        storeroom_id: int,
        received_by_id: int,
        created_by_id: int,
        carrier: str | None = None,
        tracking_number: str | None = None,
        notes: str | None = None,
        status: str = "Received",
    ) -> ArrivalHeader:
        if not package_number or not package_number.strip():
            raise ValueError("package_number is required")
        if not major_location_id:
            raise ValueError("major_location_id is required")
        if not storeroom_id:
            raise ValueError("storeroom_id is required")

        ArrivalFactory.ensure_package_number_unique(package_number.strip())

        pkg = ArrivalHeader(
            package_number=package_number.strip(),
            major_location_id=int(major_location_id),
            storeroom_id=int(storeroom_id),
            received_by_id=received_by_id,
            received_date=date.today(),
            status=status,
            carrier=carrier,
            tracking_number=tracking_number,
            notes=notes,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(pkg)
        return pkg

    @staticmethod
    def ensure_package_number_unique(package_number: str) -> None:
        existing = ArrivalHeader.query.filter_by(package_number=package_number).first()
        if existing:
            raise ValueError(
                f"Package number '{package_number}' already exists. Please use a unique package number."
            )

    @staticmethod
    def validate_storeroom_location_match(major_location_id: int, storeroom_id: int) -> None:
        storeroom = Storeroom.query.get(storeroom_id)
        if not storeroom or storeroom.major_location_id != major_location_id:
            raise ValueError("Storeroom must belong to the selected location")

    @staticmethod
    def _remaining_qty_for_receipt(line: PurchaseOrderLine) -> float:
        """Calculate remaining quantity that can be received for a PO line."""
        return max(
            0.0,
            float(line.quantity_ordered or 0.0) - float(line.quantity_received_total or 0.0),
        )

    @staticmethod
    def add_part_arrival(
        *,
        package_header_id: int,
        part_data: dict,
        major_location_id: int,
        storeroom_id: int,
        created_by_id: int,
        status: str = "Received",
        auto_link_if_available: bool = True,
    ) -> ArrivalLine:
        """
        Unified method: add an ArrivalLine row from a part dict, optionally linking it to PO lines.

        The part_data dict should contain:
        - part_id (int, required)
        - quantity_received (float, required)
        - purchase_order_line_id (int, optional) - if present, will link to this PO line
        - condition (str, optional) - Good/Damaged/Mixed (default: 'Good')
        - inspection_notes (str, optional)

        Linking behavior:
        - If purchase_order_line_id is present in part_data, attempt to link to that line.
        - Else if auto_link_if_available, find PO lines that can absorb the quantity and link.
        - Otherwise leave as unlinked.
        """
        part_id = part_data.get("part_id")
        if not part_id:
            raise ValueError("part_id is required in part_data")
        
        quantity_received = part_data.get("quantity_received")
        if quantity_received is None:
            raise ValueError("quantity_received is required in part_data")
        
        try:
            qty = float(quantity_received)
        except (TypeError, ValueError):
            raise ValueError("quantity_received must be a number")
        if qty <= 0:
            raise ValueError("quantity_received must be > 0")

        purchase_order_line_id = part_data.get("purchase_order_line_id")
        manager = ArrivalLinkageManager()

        # Create arrival line without direct PO line link
        arrival = ArrivalLine(
            package_header_id=package_header_id,
            part_id=int(part_id),
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            quantity_received=qty,
            received_date=date.today(),
            status=status,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        
        # Set inspection notes if provided
        if "inspection_notes" in part_data:
            arrival.inspection_notes = part_data.get("inspection_notes")
        
        db.session.add(arrival)

        # Handle linking
        linked_po_lines = []  # Track all PO lines that get linked for expected_delivery_date update
        if purchase_order_line_id is not None:
            # Link to specific PO line
            po_line = PurchaseOrderLine.query.get_or_404(purchase_order_line_id)
            # Ensure part consistency with the requested linkage target
            if po_line.part_id != int(part_id):
                raise ValueError(f"Part ID mismatch: arrival has part {part_id}, PO line has part {po_line.part_id}")
            
            ok, msg, link = manager.apply_link(
                arrival=arrival,
                po_line=po_line,
                quantity_to_link=qty,
                user_id=created_by_id,
            )
            if not ok:
                raise ValueError(msg)
            linked_po_lines.append(po_line)
        elif auto_link_if_available:
            # Find and link to available PO lines
            po_lines = ArrivalPOLineFinderService.find_linkable_po_lines(
                part_id=int(part_id),
                quantity_to_receive=qty,
                major_location_id=major_location_id,
            )
            remaining_qty = qty
            for po_line in po_lines:
                if remaining_qty <= 0:
                    break
                
                # Calculate how much we can link to this PO line
                qty_remaining_on_po = ArrivalPOLineFinderService.qty_needed_on_po_line(po_line)
                link_qty = min(remaining_qty, qty_remaining_on_po)
                
                if link_qty > 0:
                    ok, msg, link = manager.apply_link(
                        arrival=arrival,
                        po_line=po_line,
                        quantity_to_link=link_qty,
                        user_id=created_by_id,
                    )
                    if ok:
                        remaining_qty -= link_qty
                        linked_po_lines.append(po_line)
                    else:
                        logger.warning(f"Failed to auto-link to PO line {po_line.id}: {msg}")

        # Update expected_delivery_date for linked PO lines that don't have one set
        for po_line in linked_po_lines:
            if po_line.expected_delivery_date is None:
                po_line.expected_delivery_date = date.today()
                logger.debug(f"Updated expected_delivery_date to {date.today()} for PO line {po_line.id}")

        return arrival

    @staticmethod
    def _normalize_parts(parts: list[dict] | None) -> list[dict]:
        """
        Normalize part data from various input formats into a consistent structure.

        Expected input items can have:
          - part_id (int, required)
          - quantity or quantity_received (float, required)
          - purchase_order_line_id (int, optional) - if present, will link to this PO line
          - condition (str, optional) - Good/Damaged/Mixed (default: 'Good')
          - inspection_notes (str, optional)
        
        Output items will have:
          - part_id (int)
          - quantity_received (float)
          - purchase_order_line_id (int, optional)
          - condition (str, optional)
          - inspection_notes (str, optional)
        """
        if not parts:
            return []

        if not isinstance(parts, list):
            raise ValueError("parts must be a list")

        out: list[dict] = []
        for idx, item in enumerate(parts, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"Invalid part at line {idx}")

            part_id = item.get("part_id")
            if not part_id:
                raise ValueError(f"part_id is required for part line {idx}")

            # Support both "quantity" and "quantity_received" for backward compatibility
            qty = item.get("quantity_received") or item.get("quantity")
            if qty is None:
                raise ValueError(f"quantity or quantity_received is required for part line {idx}")

            try:
                qty_f = float(qty)
            except (TypeError, ValueError):
                raise ValueError(f"quantity must be a number for part line {idx}")

            if qty_f <= 0:
                raise ValueError(f"quantity must be > 0 for part line {idx}")

            normalized = {
                "part_id": int(part_id),
                "quantity_received": qty_f,
            }
            
            # Include purchase_order_line_id if present (determines linking behavior)
            if "purchase_order_line_id" in item:
                normalized["purchase_order_line_id"] = item.get("purchase_order_line_id")
            
            # Include condition if present
            if "condition" in item:
                condition = item.get("condition", "Good")
                if condition in ["Good", "Damaged", "Mixed"]:
                    normalized["condition"] = condition
            
            # Include inspection_notes if present
            if "inspection_notes" in item:
                normalized["inspection_notes"] = item.get("inspection_notes")

            out.append(normalized)

        return out

    @staticmethod
    def add_part_arrivals(
        *,
        package_header_id: int,
        parts: list[dict],
        created_by_id: int,
        status: str = "Received",
        auto_link_if_available: bool = True,
    ) -> list[ArrivalLine]:
        """
        Add part arrivals to an existing package header and create inventory.
        
        This method performs the following operations atomically (within the current session):
        1. Creates ArrivalLine records for each part
        2. Links arrivals to purchase order lines (if specified or auto-linked)
        3. Creates InventoryMovement records (audit trail for receipt)
        4. Updates ActiveInventory (adds quantity to unassigned bin)
        5. Updates InventorySummary (updates part-level totals and rolling average cost)
        
        **Transaction Note**: This method does NOT commit the session.
        All operations are performed within the current database session.
        The caller must commit or rollback the transaction.

        Each part in the parts list can optionally have purchase_order_line_id.
        If present, the arrival will be linked to that PO line.
        If not present and auto_link_if_available is True, will attempt to auto-link.

        Args:
            package_header_id: ID of the package header (must have major_location_id and storeroom_id)
            parts: List of part dictionaries (see add_part_arrival for format)
            created_by_id: User ID creating the arrivals
            status: Status for the arrivals (default: "Received")
            auto_link_if_available: Whether to auto-link to available PO lines
            
        Returns:
            List of created ArrivalLine instances
            
        Raises:
            ValueError: If package is missing major_location_id or storeroom_id
        """
        if not parts:
            return []

        pkg = ArrivalHeader.query.get_or_404(package_header_id)
        if not pkg.major_location_id:
            raise ValueError("package major_location_id is required")
        if not pkg.storeroom_id:
            raise ValueError("package storeroom_id is required")

        inventory_manager = InventoryManager()
        created: list[ArrivalLine] = []

        for part_data in parts:
            arrival = ArrivalFactory.add_part_arrival(
                package_header_id=pkg.id,
                part_data=part_data,
                major_location_id=pkg.major_location_id,
                storeroom_id=pkg.storeroom_id,
                created_by_id=created_by_id,
                status=status,
                auto_link_if_available=auto_link_if_available,
            )
            db.session.flush()

            # Create inventory movement and update active inventory
            # Reference the first linked PO line if any links exist (for traceability)
            # Note: A single movement can only reference one PO line, so we use the first link
            # All links are still tracked via ArrivalPurchaseOrderLink for full traceability
            links = arrival.po_line_links.all()
            po_line_id_for_movement = (
                links[0].purchase_order_line_id
                if links
                else None
            )
            
            # Create receipt movement and update inventory atomically
            # This creates:
            # 1. InventoryMovement record (audit trail)
            # 2. Updates ActiveInventory (bin-level inventory)
            # 3. Updates InventorySummary (part-level totals)
            inventory_manager.record_receipt_into_unassigned_bin(
                part_id=arrival.part_id,
                storeroom_id=pkg.storeroom_id,
                major_location_id=pkg.major_location_id,
                quantity_received=float(arrival.quantity_received or 0.0),
                purchase_order_line_id=po_line_id_for_movement,
                part_arrival_id=arrival.id,
            )
            created.append(arrival)

        return created

    # -------------------------------------------------------------------------
    # High-level workflow constructor
    # -------------------------------------------------------------------------

    @staticmethod
    def from_dict(
        arrival_data: dict,
        *,
        received_by_id: int,
        created_by_id: int,
        validate_po_lines_for_receipt: bool = True,
    ) -> int:
        """
        Unified entry point: create a package arrival from a dict.
        
        This method creates arrivals and automatically creates inventory:
        - Creates ArrivalHeader and ArrivalLine records
        - Links arrivals to purchase order lines (if specified)
        - Creates InventoryMovement records (audit trail)
        - Updates ActiveInventory (bin-level inventory)
        - Updates InventorySummary (part-level totals)
        
        **Transaction Note**: This method does NOT commit the session.
        The caller is responsible for committing or rolling back the transaction.
        All operations are performed within the current database session.

        The arrival_data dict should contain:
        - header (dict): package header information
          - package_number (str, required)
          - major_location_id (int, required) - MUST be provided
          - storeroom_id (int, required) - MUST be provided
          - tracking_number (str, optional)
          - carrier (str, optional)
          - notes (str, optional)
        - parts (list[dict], optional): list of parts to receive
          Each part dict can contain:
          - part_id (int, required)
          - quantity_received (float, required)
          - purchase_order_line_id (int, optional) - if present, will link to this PO line
          - condition (str, optional) - Good/Damaged/Mixed (default: 'Good')
          - inspection_notes (str, optional)

        For backward compatibility, also supports:
        - po_line_ids (list[int], optional): legacy parameter for PO line IDs
        - unlinked_parts (list[dict], optional): legacy parameter for unlinked parts

        If po_line_ids or unlinked_parts are provided, they will be converted to the parts format.
        
        Raises:
            ValueError: If validation fails (missing required fields, invalid data, etc.)
        """
        header = ArrivalFactory._parse_header(arrival_data)
        ArrivalFactory.ensure_package_number_unique(header.package_number)
        ArrivalFactory.validate_storeroom_location_match(header.major_location_id, header.storeroom_id)

        # Extract parts from the dict - support both new format (parts) and legacy formats
        parts: list[dict] = []
        
        # New unified format: parts list with optional purchase_order_line_id
        if "parts" in arrival_data:
            parts = ArrivalFactory._normalize_parts(arrival_data.get("parts"))
        
        # Legacy format: po_line_ids - convert to parts format
        if "po_line_ids" in arrival_data:
            po_line_ids = arrival_data.get("po_line_ids") or []
            if po_line_ids:
                lines = PurchaseOrderLine.query.filter(PurchaseOrderLine.id.in_(po_line_ids)).all()
                if len(lines) != len(po_line_ids):
                    found = {l.id for l in lines}
                    missing = [str(i) for i in po_line_ids if i not in found]
                    raise ValueError(f"One or more PO lines not found: {', '.join(missing[:10])}")
                
                if validate_po_lines_for_receipt:
                    is_valid, errors = ArrivalPOLineSelectionService.validate_lines_for_receipt(po_line_ids)
                    if not is_valid:
                        raise ValueError("Validation error: " + "; ".join(errors))
                
                # Convert PO lines to parts format with purchase_order_line_id
                for line in lines:
                    remaining = ArrivalFactory._remaining_qty_for_receipt(line)
                    if remaining <= 0:
                        continue
                    parts.append({
                        "part_id": line.part_id,
                        "quantity_received": remaining,
                        "purchase_order_line_id": line.id,
                    })
        
        # Legacy format: unlinked_parts - convert to parts format (no purchase_order_line_id)
        if "unlinked_parts" in arrival_data:
            unlinked = ArrivalFactory._normalize_parts(arrival_data.get("unlinked_parts"))
            parts.extend(unlinked)

        if not parts:
            raise ValueError("No parts specified for arrival")

        # Create package header
        pkg = ArrivalFactory.create_package_header(
            package_number=header.package_number,
            major_location_id=header.major_location_id,
            storeroom_id=header.storeroom_id,
            received_by_id=received_by_id,
            created_by_id=created_by_id,
            carrier=header.carrier,
            tracking_number=header.tracking_number,
            notes=header.notes,
        )
        db.session.flush()

        # Add all parts (they may or may not have purchase_order_line_id)
        ArrivalFactory.add_part_arrivals(
            package_header_id=pkg.id,
            parts=parts,
            created_by_id=created_by_id,
            status="Received",
            auto_link_if_available=True,
        )

        # Ensure "touched" for audit
        pkg.updated_by_id = created_by_id
        db.session.flush()

        logger.info(
            f"Created package arrival {pkg.id} ({pkg.package_number}) "
            f"with {len(parts)} parts"
        )
        return pkg.id

