from __future__ import annotations

from datetime import date

from app import db
from app.buisness.inventory.arrivals.arrival_linkage_manager import ArrivalLinkageManager
from app.buisness.inventory.stock.inventory_manager import InventoryManager
from app.data.inventory.arrivals.package_header import PackageHeader
from app.data.inventory.arrivals.part_arrival import PartArrival
from app.data.inventory.ordering.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine


class PackageArrivalContext:
    """
    Package arrival operations.

    Supports lifecycle decisions:
    - package is directly linkable to one purchase order -> auto-create part arrivals line-by-line
    - otherwise: create package header and allow manual creation/linking of part arrivals
    """

    def __init__(self, package_header_id: int):
        self.package_header_id = package_header_id

    @property
    def package(self) -> PackageHeader:
        return PackageHeader.query.get_or_404(self.package_header_id)
    
    @property
    def linkage_manager(self) -> ArrivalLinkageManager:
        """
        Convenience accessor for the arrival linkage manager.
        
        The manager is stateless and can be used for linking/unlinking
        part arrivals to PO lines.
        """
        return ArrivalLinkageManager()

    @classmethod
    def create_for_purchase_order(
        cls,
        *,
        purchase_order_id: int,
        package_number: str,
        major_location_id: int,
        storeroom_id: int,
        received_by_id: int,
        created_by_id: int,
    ) -> "PackageArrivalContext":
        po = PurchaseOrderHeader.query.get_or_404(purchase_order_id)

        pkg = PackageHeader(
            package_number=package_number,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            received_by_id=received_by_id,
            received_date=date.today(),
            status="Received",
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(pkg)
        db.session.flush()

        # Auto-create one PartArrival row per PO line (qty defaults to qty ordered remaining)
        for line in po.purchase_order_lines:
            remaining = max(0.0, (line.quantity_ordered or 0.0) - (line.quantity_received_total or 0.0))
            if remaining <= 0:
                continue
            arrival = PartArrival(
                package_header_id=pkg.id,
                purchase_order_line_id=line.id,
                part_id=line.part_id,
                major_location_id=major_location_id,
                storeroom_id=storeroom_id,
                quantity_received=remaining,
                received_date=date.today(),
                status="Arrived",
                created_by_id=created_by_id,
                updated_by_id=created_by_id,
            )
            db.session.add(arrival)

        return cls(pkg.id)

    @classmethod
    def create_from_purchase_order_lines(
        cls,
        *,
        po_line_ids: list[int],
        package_number: str,
        major_location_id: int,
        storeroom_id: int,
        received_by_id: int,
        created_by_id: int,
    ) -> "PackageArrivalContext":
        """
        Factory Pattern 2: Create a package arrival directly from selected PO lines.

        Assumptions:
        - Caller has validated these lines are eligible for full acceptance (no partial/rejected workflow here).
        - For each PO line, we create one PartArrival with quantity_received equal to the remaining unfulfilled qty.
        """
        if not po_line_ids:
            raise ValueError("po_line_ids must not be empty")

        lines = PurchaseOrderLine.query.filter(PurchaseOrderLine.id.in_(po_line_ids)).all()
        if len(lines) != len(po_line_ids):
            found = {l.id for l in lines}
            missing = [str(i) for i in po_line_ids if i not in found]
            raise ValueError(f"One or more PO lines not found: {', '.join(missing[:10])}")

        pkg = PackageHeader(
            package_number=package_number,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            received_by_id=received_by_id,
            received_date=date.today(),
            status="Received",
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(pkg)
        db.session.flush()

        # Create one PartArrival row per selected PO line (qty defaults to remaining unfulfilled)
        for line in lines:
            remaining = max(
                0.0,
                float(line.quantity_ordered or 0.0)
                - (float(line.quantity_accepted or 0.0) + float(line.quantity_rejected or 0.0)),
            )
            if remaining <= 0:
                continue

            arrival = PartArrival(
                package_header_id=pkg.id,
                purchase_order_line_id=line.id,
                part_id=line.part_id,
                major_location_id=major_location_id,
                storeroom_id=storeroom_id,
                quantity_received=remaining,
                received_date=date.today(),
                status="Arrived",
                created_by_id=created_by_id,
                updated_by_id=created_by_id,
            )
            db.session.add(arrival)

        return cls(pkg.id)

    @classmethod
    def create_unlinked(
        cls,
        *,
        package_number: str,
        major_location_id: int,
        storeroom_id: int,
        received_by_id: int,
        part_arrivals: list[dict],
        created_by_id: int,
        carrier: str | None = None,
        tracking_number: str | None = None,
        notes: str | None = None,
    ) -> "PackageArrivalContext":
        """
        Factory Pattern 3: Create an "unlinked" arrival from user-defined part arrivals.

        Important implementation detail:
        - Current schema requires PartArrival.purchase_order_line_id (non-null FK).
          To support "unlinked" receipts, we create placeholder PO header/lines and mark
          them as `is_fake_for_inventory_adjustments=True`.
        - We create arrivals in Accepted status and immediately create receipt inventory movements.

        Args:
            package_number: Unique package identifier.
            major_location_id: Required location for arrivals and movements.
            storeroom_id: Required to receive into unassigned bin inventory.
            received_by_id: User who received the package.
            part_arrivals: List of dicts with:
                - part_id (required int)
                - quantity_received (required float > 0)
                - inspection_notes (optional str)
            created_by_id: User ID for audit fields.
            carrier/tracking_number/notes: Optional PackageHeader metadata.
        """
        if not package_number or not package_number.strip():
            raise ValueError("package_number is required")
        if not major_location_id:
            raise ValueError("major_location_id is required")
        if not storeroom_id:
            raise ValueError("storeroom_id is required")
        if not part_arrivals:
            raise ValueError("part_arrivals must not be empty")

        # Create package header
        pkg = PackageHeader(
            package_number=package_number.strip(),
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            received_by_id=received_by_id,
            received_date=date.today(),
            status="Received",
            carrier=carrier,
            tracking_number=tracking_number,
            notes=notes,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(pkg)
        db.session.flush()

        inventory_manager = InventoryManager()

        # Create Accepted arrivals + inventory receipts (no PO link)
        for idx, item in enumerate(part_arrivals, start=1):
            part_id = item.get("part_id")
            if not part_id:
                raise ValueError(f"part_id is required for part_arrivals line {idx}")

            qty = item.get("quantity_received")
            if qty is None:
                raise ValueError(f"quantity_received is required for part_arrivals line {idx}")
            try:
                qty_f = float(qty)
            except (TypeError, ValueError):
                raise ValueError(f"quantity_received must be a number for part_arrivals line {idx}")
            if qty_f <= 0:
                raise ValueError(f"quantity_received must be > 0 for part_arrivals line {idx}")

            arrival = PartArrival(
                package_header_id=pkg.id,
                purchase_order_line_id=None,
                part_id=int(part_id),
                major_location_id=major_location_id,
                storeroom_id=storeroom_id,
                quantity_received=qty_f,
                received_date=date.today(),
                status="Accepted",
                inspection_notes=item.get("inspection_notes"),
                created_by_id=created_by_id,
                updated_by_id=created_by_id,
            )
            db.session.add(arrival)
            db.session.flush()

            # Create receipt movement and update ActiveInventory/InventorySummary
            inventory_manager.record_receipt_into_unassigned_bin(
                part_id=arrival.part_id,
                storeroom_id=storeroom_id,
                major_location_id=major_location_id,
                quantity_received_accepted=qty_f,
                purchase_order_line_id=None,
                part_arrival_id=arrival.id,
            )

        return cls(pkg.id)

    def add_part_arrival_for_purchase_order_line(
        self,
        *,
        purchase_order_line_id: int,
        quantity_received: float,
        major_location_id: int,
        storeroom_id: int,
        created_by_id: int,
    ) -> PartArrival:
        """
        Manual path for packages that are not directly linkable.

        Caller is responsible for selecting the correct purchase order line.
        """
        if quantity_received <= 0:
            raise ValueError("quantity_received must be > 0")

        # Derive part from the purchase order line for consistency
        from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine

        line = PurchaseOrderLine.query.get_or_404(purchase_order_line_id)
        arrival = PartArrival(
            package_header_id=self.package_header_id,
            purchase_order_line_id=line.id,
            part_id=line.part_id,
            major_location_id=major_location_id,
            storeroom_id=storeroom_id,
            quantity_received=quantity_received,
            received_date=date.today(),
            status="Arrived",
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        db.session.add(arrival)
        return arrival


