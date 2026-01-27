"""
Part Demand Search Service
Service layer for searching and filtering part demands in inventory module
"""

from typing import List, Optional, Iterable
from datetime import datetime, timedelta
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload

from app.logger import get_logger
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.core.asset_info.asset import Asset
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.supply.part_definition import PartDefinition

logger = get_logger("asset_management.services.inventory.purchasing.part_demand_search")


class PartDemandSearchService:
    """Service for searching and filtering part demands"""
    
    # Orderable statuses (for inventory use case)
    ORDERABLE_PART_DEMAND_STATUSES: set[str] = {
        "Planned",
        "Pending Manager Approval",
        "Pending Inventory Approval",
    }
    
    BLOCKED_PART_DEMAND_STATUSES: set[str] = {
        "Issued",
        "Ordered",
        "Installed",
    }
    
    @staticmethod
    def get_filtered_part_demands(
        part_id: Optional[int] = None,
        part_description: Optional[str] = None,
        maintenance_event_id: Optional[int] = None,
        asset_id: Optional[int] = None,
        asset_type_id: Optional[int] = None,
        make: Optional[str] = None,
        model: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
        major_location_id: Optional[int] = None,
        status: Optional[str] = None,
        sort_by: Optional[str] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        updated_from: Optional[datetime] = None,
        updated_to: Optional[datetime] = None,
        maintenance_event_created_from: Optional[datetime] = None,
        maintenance_event_created_to: Optional[datetime] = None,
        maintenance_event_updated_from: Optional[datetime] = None,
        maintenance_event_updated_to: Optional[datetime] = None,
        exclude_part_demand_ids: Optional[Iterable[int]] = None,
        limit: int = 1000,
        default_to_orderable: bool = True
    ) -> List[PartDemand]:
        """
        Get filtered part demands with all related data loaded.
        
        Args:
            part_id: Filter by part ID
            part_description: Filter by part description (partial match)
            maintenance_event_id: Filter by maintenance event ID
            asset_id: Filter by asset ID
            assigned_to_id: Filter by assigned user ID
            major_location_id: Filter by major location ID
            status: Filter by status
            sort_by: Sort option ('price_asc', 'price_desc', 'date_asc', 'date_desc')
            created_from: Filter by creation date from (inclusive)
            created_to: Filter by creation date to (inclusive)
            updated_from: Filter by last updated date from (inclusive)
            updated_to: Filter by last updated date to (inclusive)
            maintenance_event_created_from: Filter by maintenance event creation date from (inclusive)
            maintenance_event_created_to: Filter by maintenance event creation date to (inclusive)
            maintenance_event_updated_from: Filter by maintenance event last updated date from (inclusive)
            maintenance_event_updated_to: Filter by maintenance event last updated date to (inclusive)
            limit: Maximum number of results
            default_to_orderable: If True and no status filter, default to orderable statuses (inventory use case)
            
        Returns:
            List of PartDemand objects with relationships loaded
        """
        query = PartDemand.query.options(
            joinedload(PartDemand.action)
            .joinedload(Action.maintenance_action_set)
            .joinedload(MaintenanceActionSet.asset)
            .joinedload(Asset.make_model),
            joinedload(PartDemand.action)
            .joinedload(Action.maintenance_action_set)
            .joinedload(MaintenanceActionSet.asset)
            .joinedload(Asset.asset_type),
            joinedload(PartDemand.part),
            joinedload(PartDemand.requested_by),
        )
        
        # Track if we need to join PartDefinition for sorting
        needs_part_join_for_sort = sort_by in ['price_asc', 'price_desc']
        needs_part_join = bool(part_description) or needs_part_join_for_sort
        
        # Filter by part ID
        if part_id:
            query = query.filter(PartDemand.part_id == part_id)
        
        # Exclude specific part demands
        if exclude_part_demand_ids:
            exclude_ids = [int(x) for x in exclude_part_demand_ids if x is not None]
            if exclude_ids:
                query = query.filter(~PartDemand.id.in_(exclude_ids))

        # Filter by part description or join for sorting
        if needs_part_join:
            query = query.join(PartDefinition, PartDemand.part_id == PartDefinition.id)
            if part_description:
                query = query.filter(
                    or_(
                        PartDefinition.part_name.ilike(f'%{part_description}%'),
                        PartDefinition.description.ilike(f'%{part_description}%')
                    )
                )
        
        # Maintenance event filters - join once if any of these filters are used
        needs_maintenance_join = any([
            maintenance_event_id, asset_id, asset_type_id, assigned_to_id, major_location_id,
            make, model,
            maintenance_event_created_from, maintenance_event_created_to,
            maintenance_event_updated_from, maintenance_event_updated_to
        ])
        if needs_maintenance_join:
            query = query.join(Action).join(MaintenanceActionSet)
            
            # Filter by maintenance event ID
            if maintenance_event_id:
                query = query.filter(MaintenanceActionSet.event_id == maintenance_event_id)
            
            # Filter by asset ID
            if asset_id:
                query = query.filter(MaintenanceActionSet.asset_id == asset_id)
            
            # Filter by assigned user
            if assigned_to_id:
                query = query.filter(MaintenanceActionSet.assigned_user_id == assigned_to_id)
            
            # Asset-level filters - join Asset when needed
            needs_asset_join = any([major_location_id, asset_type_id, make, model])
            if needs_asset_join:
                query = query.join(Asset, MaintenanceActionSet.asset_id == Asset.id)

                if major_location_id:
                    query = query.filter(Asset.major_location_id == major_location_id)

                if asset_type_id:
                    query = query.filter(Asset.asset_type_id == asset_type_id)

                # Make/Model filters (partial match, case-insensitive)
                make_s = (make or "").strip()
                model_s = (model or "").strip()
                if make_s or model_s:
                    query = query.join(MakeModel, Asset.make_model_id == MakeModel.id)
                    if make_s:
                        query = query.filter(MakeModel.make.ilike(f"%{make_s}%"))
                    if model_s:
                        query = query.filter(MakeModel.model.ilike(f"%{model_s}%"))
            
            # Filter by maintenance event creation date range
            if maintenance_event_created_from:
                query = query.filter(MaintenanceActionSet.created_at >= maintenance_event_created_from)
            if maintenance_event_created_to:
                # If caller passed a date-only value, make it inclusive of the whole day.
                # If caller passed a datetime with a time component (e.g. datetime-local), treat it as an exact upper bound.
                if maintenance_event_created_to.time() == datetime.min.time():
                    maintenance_event_created_to_end = maintenance_event_created_to + timedelta(days=1)
                    query = query.filter(MaintenanceActionSet.created_at < maintenance_event_created_to_end)
                else:
                    query = query.filter(MaintenanceActionSet.created_at <= maintenance_event_created_to)
            
            # Filter by maintenance event updated date range
            if maintenance_event_updated_from:
                query = query.filter(MaintenanceActionSet.updated_at >= maintenance_event_updated_from)
            if maintenance_event_updated_to:
                if maintenance_event_updated_to.time() == datetime.min.time():
                    maintenance_event_updated_to_end = maintenance_event_updated_to + timedelta(days=1)
                    query = query.filter(MaintenanceActionSet.updated_at < maintenance_event_updated_to_end)
                else:
                    query = query.filter(MaintenanceActionSet.updated_at <= maintenance_event_updated_to)
        
        # Filter by status
        if status:
            query = query.filter(PartDemand.status == status)
        
        # Filter by creation date range
        if created_from:
            query = query.filter(PartDemand.created_at >= created_from)
        if created_to:
            if created_to.time() == datetime.min.time():
                created_to_end = created_to + timedelta(days=1)
                query = query.filter(PartDemand.created_at < created_to_end)
            else:
                query = query.filter(PartDemand.created_at <= created_to)
        
        # Filter by updated date range
        if updated_from:
            query = query.filter(PartDemand.updated_at >= updated_from)
        if updated_to:
            if updated_to.time() == datetime.min.time():
                updated_to_end = updated_to + timedelta(days=1)
                query = query.filter(PartDemand.updated_at < updated_to_end)
            else:
                query = query.filter(PartDemand.updated_at <= updated_to)
        
        # Apply sorting
        if sort_by in ['price_asc', 'price_desc']:
            # Calculate QTY * last_unit_cost, handling NULL values
            # If last_unit_cost is NULL, treat it as 0 for sorting purposes
            price_calculation = func.coalesce(
                PartDemand.quantity_required * func.coalesce(PartDefinition.last_unit_cost, 0),
                0
            )
            if sort_by == 'price_asc':
                query = query.order_by(price_calculation.asc())
            else:  # price_desc
                query = query.order_by(price_calculation.desc())
        elif sort_by in ['date_asc', 'date_desc']:
            # Sort by creation date
            if sort_by == 'date_asc':
                query = query.order_by(PartDemand.created_at.asc())
            else:  # date_desc
                query = query.order_by(PartDemand.created_at.desc())
        
        # Use distinct to avoid duplicates from joins
        query = query.distinct()
        
        demands = query.limit(limit).all()
        
        # If no status filter and default_to_orderable, filter to orderable statuses
        if default_to_orderable and not status:
            filtered = [
                d for d in demands
                if (d.status in PartDemandSearchService.ORDERABLE_PART_DEMAND_STATUSES) 
                and (d.status not in PartDemandSearchService.BLOCKED_PART_DEMAND_STATUSES)
            ]
            return filtered
        
        return demands
    
    @staticmethod
    def get_filter_options():
        """Return dropdown options used by the portal filter UI."""
        from app import db
        from app.data.core.major_location import MajorLocation
        from app.data.core.user_info.user import User
        from app.data.maintenance.base.part_demands import PartDemand
        
        # Status options: only show statuses relevant to ordering + any existing statuses.
        statuses = db.session.query(PartDemand.status).distinct().all()
        status_options = sorted({s[0] for s in statuses if s[0]})

        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        locations = MajorLocation.query.filter_by(is_active=True).order_by(MajorLocation.name).all()

        return {
            "status_options": status_options,
            "users": users,
            "locations": locations,
        }
    
    @staticmethod
    def get_demands_by_ids(part_demand_ids: list[int]) -> list[PartDemand]:
        """Get part demands by their IDs, preserving input order."""
        if not part_demand_ids:
            return []

        demands = (
            PartDemand.query.filter(PartDemand.id.in_(part_demand_ids))
            .options(
                joinedload(PartDemand.part),
                joinedload(PartDemand.requested_by),
                joinedload(PartDemand.action).joinedload(Action.maintenance_action_set),
            )
            .all()
        )

        # Preserve input order
        by_id = {d.id: d for d in demands}
        return [by_id[i] for i in part_demand_ids if i in by_id]
    
    @staticmethod
    def build_parts_summary(selected_demands: list[PartDemand]) -> list[dict]:
        """Group selected demands by part_id and compute total required qty."""
        totals: dict[int, float] = {}
        for d in selected_demands:
            totals[d.part_id] = float(totals.get(d.part_id, 0.0) + (d.quantity_required or 0.0))

        part_ids = list(totals.keys())
        parts = PartDefinition.query.filter(PartDefinition.id.in_(part_ids)).all() if part_ids else []
        parts_by_id = {p.id: p for p in parts}

        summary: list[dict] = []
        for part_id, total_qty in sorted(totals.items(), key=lambda x: x[0]):
            part = parts_by_id.get(part_id)
            summary.append(
                {
                    "part_id": part_id,
                    "part_number": part.part_number if part else str(part_id),
                    "part_name": part.part_name if part else "",
                    "total_qty": total_qty,
                    "default_unit_cost": float(part.last_unit_cost) if (part and part.last_unit_cost) else 0.0,
                }
            )

        return summary
    
    @staticmethod
    def normalize_selected_ids(raw_ids: list[str]) -> list[int]:
        """Normalize and de-duplicate selected part demand IDs."""
        ids: list[int] = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except Exception:
                continue
        # de-dupe, stable
        seen: set[int] = set()
        out: list[int] = []
        for i in ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out
