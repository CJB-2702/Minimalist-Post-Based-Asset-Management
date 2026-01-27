"""
PO Linkage Lookup Service
Service for finding unlinked part demands for purchase order linkage portal.
Reuses PartDemandSearchService for consistent search logic.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import joinedload

from app.logger import get_logger
from app import db
from app.data.inventory.purchasing.part_demand_link import PartDemandPurchaseOrderLink
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.services.inventory.purchasing.part_demand_search_service import PartDemandSearchService

logger = get_logger("asset_management.services.inventory.purchasing.po_linkage_lookup")


class POLinkageLookupService:
    """Service for finding unlinked part demands for PO linkage"""
    
    @staticmethod
    def get_all_linked_demand_ids() -> set[int]:
        """
        Get all part demand IDs that are already linked to any PO line.
        This excludes demands that are already linked anywhere, not just to a specific PO.
        
        Returns:
            Set of part_demand_ids that are already linked
        """
        linked_ids = (
            db.session.query(PartDemandPurchaseOrderLink.part_demand_id)
            .distinct()
            .all()
        )
        return {row[0] for row in linked_ids}
    
    @staticmethod
    def get_maintenance_events_with_demands(
        po_id: Optional[int] = None,
        part_id: Optional[int] = None,
        asset_id: Optional[int] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        asset_type_id: Optional[int] = None,
        major_location_id: Optional[int] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        assigned_user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get maintenance events that have unlinked part demands.
        Uses PartDemandSearchService to find matching demands, then groups by event.
        Excludes demands that are already linked to any PO.
        
        Args:
            po_id: Optional purchase order ID (for logging/context, not used for filtering linked demands)
            part_id: Filter by part ID
            asset_id: Filter by asset ID
            make: Filter by make (partial match)
            model: Filter by model (partial match)
            asset_type_id: Filter by asset type ID
            major_location_id: Filter by major location ID
            created_from: Filter by maintenance event creation date from
            created_to: Filter by maintenance event creation date to
            assigned_user_id: Filter by assigned user ID
            
        Returns:
            List of dictionaries with event_id, maintenance_action_set, and demands
        """
        # Get all linked demand IDs (across all POs)
        all_linked_demand_ids = POLinkageLookupService.get_all_linked_demand_ids()
        
        # Use PartDemandSearchService to find unlinked demands
        unlinked_demands = PartDemandSearchService.get_filtered_part_demands(
            part_id=part_id,
            asset_id=asset_id,
            asset_type_id=asset_type_id,
            make=make,
            model=model,
            assigned_to_id=assigned_user_id,
            major_location_id=major_location_id,
            maintenance_event_created_from=created_from,
            maintenance_event_created_to=created_to,
            exclude_part_demand_ids=all_linked_demand_ids,
            default_to_orderable=True,
            limit=2000,
        )
        
        # Group by maintenance event
        events_dict: Dict[int, Dict[str, Any]] = {}
        for demand in unlinked_demands:
            # Skip demands without proper relationships
            if not demand.action or not demand.action.maintenance_action_set:
                logger.warning(f"Part demand {demand.id} missing action or maintenance_action_set relationship")
                continue
                
            mas = demand.action.maintenance_action_set
            event_id = mas.event_id
            
            if event_id not in events_dict:
                events_dict[event_id] = {
                    "event_id": event_id,
                    "maintenance_action_set": mas,
                    "demands": []
                }
            
            events_dict[event_id]["demands"].append(demand)
        
        return list(events_dict.values())
    
    @staticmethod
    def serialize_event_data(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize event data for JSON response.
        Handles None values gracefully.
        
        Args:
            event_data: Dictionary with event_id, maintenance_action_set, and demands
            
        Returns:
            Serialized dictionary for JSON response
        """
        mas = event_data["maintenance_action_set"]
        demands = event_data["demands"]
        
        # Safely get asset name
        asset_name = None
        if mas.asset and hasattr(mas.asset, 'name'):
            asset_name = mas.asset.name
        
        # Safely get planned start datetime
        planned_start = None
        if hasattr(mas, 'planned_start_datetime') and mas.planned_start_datetime:
            planned_start = mas.planned_start_datetime.isoformat()
        
        # Serialize demands
        serialized_demands = []
        for d in demands:
            # Safely get part info
            part_number = str(d.part_id)
            part_name = ""
            if d.part:
                if hasattr(d.part, 'part_number') and d.part.part_number:
                    part_number = d.part.part_number
                if hasattr(d.part, 'part_name') and d.part.part_name:
                    part_name = d.part.part_name
            
            # Safely get action name
            action_name = ""
            if d.action and hasattr(d.action, 'action_name'):
                action_name = d.action.action_name or ""
            
            serialized_demands.append({
                "id": d.id,
                "part_id": d.part_id,
                "part_number": part_number,
                "part_name": part_name,
                "quantity_required": float(d.quantity_required) if d.quantity_required else 0.0,
                "status": d.status if d.status else "",
                "priority": d.priority if d.priority else "",
                "action_name": action_name
            })
        
        return {
            "event_id": event_data["event_id"],
            "task_name": getattr(mas, 'task_name', '') or "",
            "asset_name": asset_name,
            "asset_id": getattr(mas, 'asset_id', None),
            "status": getattr(mas, 'status', '') or "",
            "priority": getattr(mas, 'priority', '') or "",
            "planned_start": planned_start,
            "demands": serialized_demands
        }
