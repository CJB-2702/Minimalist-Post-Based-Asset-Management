"""
Part Demand Search Service
Service layer for searching and filtering part demands
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload

from app.logger import get_logger
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.core.asset_info.asset import Asset
from app.data.core.supply.part_definition import PartDefinition

logger = get_logger("asset_management.services.maintenance.part_demand_search")


class PartDemandSearchService:
    """Service for searching and filtering part demands"""
    
    @staticmethod
    def get_filtered_part_demands(
        part_id: Optional[int] = None,
        part_description: Optional[str] = None,
        maintenance_event_id: Optional[int] = None,
        asset_id: Optional[int] = None,
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
        limit: int = 1000
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
            
        Returns:
            List of PartDemand objects with relationships loaded
        """
        query = PartDemand.query.options(
            joinedload(PartDemand.action).joinedload(Action.maintenance_action_set),
            joinedload(PartDemand.part),
            joinedload(PartDemand.requested_by)
        )
        
        # Track if we need to join PartDefinition for sorting
        needs_part_join_for_sort = sort_by in ['price_asc', 'price_desc']
        needs_part_join = bool(part_description) or needs_part_join_for_sort
        
        # Filter by part ID
        if part_id:
            query = query.filter(PartDemand.part_id == part_id)
        
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
            maintenance_event_id, asset_id, assigned_to_id, major_location_id,
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
            
            # Filter by major location - need additional join to Asset
            if major_location_id:
                query = query.join(Asset)
                query = query.filter(Asset.major_location_id == major_location_id)
            
            # Filter by maintenance event creation date range
            if maintenance_event_created_from:
                query = query.filter(MaintenanceActionSet.created_at >= maintenance_event_created_from)
            if maintenance_event_created_to:
                # Add one day to make it inclusive of the entire day
                maintenance_event_created_to_end = maintenance_event_created_to + timedelta(days=1)
                query = query.filter(MaintenanceActionSet.created_at < maintenance_event_created_to_end)
            
            # Filter by maintenance event updated date range
            if maintenance_event_updated_from:
                query = query.filter(MaintenanceActionSet.updated_at >= maintenance_event_updated_from)
            if maintenance_event_updated_to:
                # Add one day to make it inclusive of the entire day
                maintenance_event_updated_to_end = maintenance_event_updated_to + timedelta(days=1)
                query = query.filter(MaintenanceActionSet.updated_at < maintenance_event_updated_to_end)
        
        # Filter by status
        if status:
            query = query.filter(PartDemand.status == status)
        
        # Filter by creation date range
        if created_from:
            query = query.filter(PartDemand.created_at >= created_from)
        if created_to:
            # Add one day to make it inclusive of the entire day
            created_to_end = created_to + timedelta(days=1)
            query = query.filter(PartDemand.created_at < created_to_end)
        
        # Filter by updated date range
        if updated_from:
            query = query.filter(PartDemand.updated_at >= updated_from)
        if updated_to:
            # Add one day to make it inclusive of the entire day
            updated_to_end = updated_to + timedelta(days=1)
            query = query.filter(PartDemand.updated_at < updated_to_end)
        
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
        
        return query.limit(limit).all()
