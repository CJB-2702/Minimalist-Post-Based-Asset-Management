from __future__ import annotations


class InventoryStatusValidator:
    """
    Centralized status transition validator for inventory-linked entities.

    This is intentionally simple (string status codes) and can be swapped to a StatusSet-based
    implementation later without changing business workflows.
    """

    # NOTE: these are conventions used by the lifecycle docs; keep them consistent.
    PURCHASE_ORDER = {"Draft", "Ordered", "Shipped", "Arrived", "Cancelled"}
    PURCHASE_ORDER_LINE = {"Pending", "Ordered", "Shipped", "Complete", "Cancelled"}
    PART_DEMAND = {
        "Manager Approval Pending",
        "Inventory Approval Pending",
        "Ordered",
        "Shipped",
        "Arrived",
        "At Inventory",
        "Issued",
        "Installed",
        "Planned",  # legacy/default in maintenance
    }
    PART_ARRIVAL = {"Pending", "Arrived", "Accepted", "Rejected"}

    _NEXT = {
        ("purchase_order", "Draft"): {"Ordered", "Cancelled"},
        ("purchase_order", "Ordered"): {"Shipped", "Cancelled"},
        ("purchase_order", "Shipped"): {"Arrived"},
        ("purchase_order", "Arrived"): set(),
        ("purchase_order", "Cancelled"): set(),
        ("purchase_order_line", "Pending"): {"Ordered", "Cancelled"},
        ("purchase_order_line", "Ordered"): {"Shipped", "Complete", "Cancelled"},
        ("purchase_order_line", "Shipped"): {"Complete"},
        ("purchase_order_line", "Complete"): set(),
        ("purchase_order_line", "Cancelled"): set(),
        ("part_arrival", "Pending"): {"Arrived", "Accepted", "Rejected"},
        ("part_arrival", "Arrived"): {"Accepted", "Rejected"},
        ("part_arrival", "Accepted"): set(),
        ("part_arrival", "Rejected"): set(),
    }

    @classmethod
    def can_transition(cls, entity_type: str, current_status: str, new_status: str) -> bool:
        allowed = cls._NEXT.get((entity_type, current_status))
        if allowed is None:
            # if we don't have rules, allow (keeps system flexible while rebuilding)
            return True
        return new_status in allowed


