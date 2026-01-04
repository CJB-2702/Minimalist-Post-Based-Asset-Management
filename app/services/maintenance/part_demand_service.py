"""
Part Demand Service
Service layer for managing part demands - approve, reject, bulk operations
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import or_, and_, func, case
from sqlalchemy.orm import joinedload

from app import db
from app.logger import get_logger
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.core.asset_info.asset import Asset
from app.data.core.supply.part_definition import PartDefinition
from app.buisness.core.event_context import EventContext

logger = get_logger("asset_management.services.maintenance.part_demand")


class PartDemandService:
    """Service for managing part demands - filtering, approval, rejection, bulk operations"""
    
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
        needs_maintenance_join = any([maintenance_event_id, asset_id, assigned_to_id, major_location_id])
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
        
        # Filter by status
        if status:
            query = query.filter(PartDemand.status == status)
        
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
    
    @staticmethod
    def approve_part_demand(part_demand_id: int, user_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Approve a part demand (manager approval).
        
        Args:
            part_demand_id: Part demand ID to approve
            user_id: User ID approving
            notes: Optional approval notes
            
        Returns:
            Dict with success status and message
            
        Raises:
            ValueError: If part demand not found or not in valid status
        """
        part_demand = PartDemand.query.get(part_demand_id)
        if not part_demand:
            raise ValueError(f"Part demand {part_demand_id} not found")
        
        # Prevent operations on items that are already Issued, Ordered, or Installed
        blocked_statuses = ['Issued', 'Ordered', 'Installed']
        if part_demand.status in blocked_statuses:
            raise ValueError(f"Cannot approve part demand in status '{part_demand.status}'. This item has already been processed.")
        
        # Validate status - should be in a state that can be approved
        valid_statuses = ['Planned', 'Requested', 'Pending Manager Approval']
        if part_demand.status not in valid_statuses:
            raise ValueError(f"Cannot approve part demand in status '{part_demand.status}'. Must be one of: {', '.join(valid_statuses)}")
        
        # Update approval fields
        part_demand.maintenance_approval_by_id = user_id
        part_demand.maintenance_approval_date = datetime.utcnow()
        part_demand.status = 'Pending Inventory Approval'
        
        db.session.commit()
        
        # Generate automated comment
        try:
            action = Action.query.get(part_demand.action_id)
            if action and action.maintenance_action_set_id:
                maintenance_action_set = MaintenanceActionSet.query.get(action.maintenance_action_set_id)
                if maintenance_action_set and maintenance_action_set.event_id:
                    event_context = EventContext(maintenance_action_set.event_id)
                    part = PartDefinition.query.get(part_demand.part_id)
                    part_name = part.part_name if part else f"Part #{part_demand.part_id}"
                    comment_text = f"[Part Demand Approved] Approved part demand: {part_name} x{part_demand.quantity_required} by user {user_id}"
                    if notes:
                        comment_text += f". Notes: {notes}"
                    event_context.add_comment(
                        user_id=user_id,
                        content=comment_text,
                        is_human_made=False
                    )
                    db.session.commit()
        except Exception as e:
            logger.warning(f"Could not add comment for part demand approval: {e}")
        
        return {'success': True, 'message': 'Part demand approved successfully'}
    
    @staticmethod
    def reject_part_demand(part_demand_id: int, user_id: int, reason: str) -> Dict[str, Any]:
        """
        Reject a part demand (manager rejection).
        
        Args:
            part_demand_id: Part demand ID to reject
            user_id: User ID rejecting
            reason: Rejection reason (required)
            
        Returns:
            Dict with success status and message
            
        Raises:
            ValueError: If part demand not found or not in valid status
        """
        if not reason or not reason.strip():
            raise ValueError("Rejection reason is required")
        
        part_demand = PartDemand.query.get(part_demand_id)
        if not part_demand:
            raise ValueError(f"Part demand {part_demand_id} not found")
        
        # Prevent operations on items that are already Issued, Ordered, or Installed
        blocked_statuses = ['Issued', 'Ordered', 'Installed']
        if part_demand.status in blocked_statuses:
            raise ValueError(f"Cannot reject part demand in status '{part_demand.status}'. This item has already been processed.")
        
        # Validate status - should be in a state that can be rejected
        # Allow rejection for Pending Inventory Approval and Pending Manager Approval
        valid_statuses = ['Planned', 'Requested', 'Pending Manager Approval', 'Pending Inventory Approval']
        if part_demand.status not in valid_statuses:
            raise ValueError(f"Cannot reject part demand in status '{part_demand.status}'. Must be one of: {', '.join(valid_statuses)}")
        
        # Update status
        part_demand.status = 'Rejected'
        if hasattr(part_demand, 'notes'):
            existing_notes = part_demand.notes or ''
            part_demand.notes = f"{existing_notes}\n[Rejected by user {user_id}] {reason}".strip()
        
        db.session.commit()
        
        # Generate automated comment
        try:
            action = Action.query.get(part_demand.action_id)
            if action and action.maintenance_action_set_id:
                maintenance_action_set = MaintenanceActionSet.query.get(action.maintenance_action_set_id)
                if maintenance_action_set and maintenance_action_set.event_id:
                    event_context = EventContext(maintenance_action_set.event_id)
                    part = PartDefinition.query.get(part_demand.part_id)
                    part_name = part.part_name if part else f"Part #{part_demand.part_id}"
                    comment_text = f"[Part Demand Rejected] Rejected part demand: {part_name} x{part_demand.quantity_required} by user {user_id}. Reason: {reason}"
                    event_context.add_comment(
                        user_id=user_id,
                        content=comment_text,
                        is_human_made=False
                    )
                    db.session.commit()
        except Exception as e:
            logger.warning(f"Could not add comment for part demand rejection: {e}")
        
        return {'success': True, 'message': 'Part demand rejected successfully'}
    
    @staticmethod
    def bulk_approve_part_demands(part_demand_ids: List[int], user_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        """
        Bulk approve multiple part demands.
        
        Args:
            part_demand_ids: List of part demand IDs to approve
            user_id: User ID approving
            notes: Optional approval notes
            
        Returns:
            Dict with success count, failure count, and details
        """
        success_count = 0
        failure_count = 0
        errors = []
        
        for part_demand_id in part_demand_ids:
            try:
                PartDemandService.approve_part_demand(part_demand_id, user_id, notes)
                success_count += 1
            except Exception as e:
                failure_count += 1
                errors.append(f"Part demand {part_demand_id}: {str(e)}")
                logger.error(f"Error approving part demand {part_demand_id}: {e}")
        
        return {
            'success': True,
            'success_count': success_count,
            'failure_count': failure_count,
            'errors': errors,
            'message': f'Approved {success_count} part demand(s), {failure_count} failed'
        }
    
    @staticmethod
    def bulk_reject_part_demands(part_demand_ids: List[int], user_id: int, reason: str) -> Dict[str, Any]:
        """
        Bulk reject multiple part demands.
        
        Args:
            part_demand_ids: List of part demand IDs to reject
            user_id: User ID rejecting
            reason: Rejection reason (required)
            
        Returns:
            Dict with success count, failure count, and details
        """
        if not reason or not reason.strip():
            raise ValueError("Rejection reason is required")
        
        success_count = 0
        failure_count = 0
        errors = []
        
        for part_demand_id in part_demand_ids:
            try:
                PartDemandService.reject_part_demand(part_demand_id, user_id, reason)
                success_count += 1
            except Exception as e:
                failure_count += 1
                errors.append(f"Part demand {part_demand_id}: {str(e)}")
                logger.error(f"Error rejecting part demand {part_demand_id}: {e}")
        
        return {
            'success': True,
            'success_count': success_count,
            'failure_count': failure_count,
            'errors': errors,
            'message': f'Rejected {success_count} part demand(s), {failure_count} failed'
        }
    
    @staticmethod
    def bulk_change_part_id(part_demand_ids: List[int], new_part_id: int, user_id: int) -> Dict[str, Any]:
        """
        Bulk change part ID for multiple part demands.
        
        Args:
            part_demand_ids: List of part demand IDs to update
            new_part_id: New part ID to set
            user_id: User ID making the change
            
        Returns:
            Dict with success count, failure count, and details
        """
        # Validate new part exists
        new_part = PartDefinition.query.get(new_part_id)
        if not new_part:
            raise ValueError(f"Part {new_part_id} not found")
        
        success_count = 0
        failure_count = 0
        errors = []
        
        for part_demand_id in part_demand_ids:
            try:
                part_demand = PartDemand.query.get(part_demand_id)
                if not part_demand:
                    raise ValueError(f"Part demand {part_demand_id} not found")
                
                # Prevent operations on items that are already Issued, Ordered, or Installed
                blocked_statuses = ['Issued', 'Ordered', 'Installed']
                if part_demand.status in blocked_statuses:
                    raise ValueError(f"Cannot change part ID for part demand in status '{part_demand.status}'. This item has already been processed.")
                
                old_part_id = part_demand.part_id
                part_demand.part_id = new_part_id
                
                # Add note about the change
                if hasattr(part_demand, 'notes'):
                    existing_notes = part_demand.notes or ''
                    part_demand.notes = f"{existing_notes}\n[Part ID changed from {old_part_id} to {new_part_id} by user {user_id}]".strip()
                
                db.session.commit()
                
                # Generate automated comment
                try:
                    action = Action.query.get(part_demand.action_id)
                    if action and action.maintenance_action_set_id:
                        maintenance_action_set = MaintenanceActionSet.query.get(action.maintenance_action_set_id)
                        if maintenance_action_set and maintenance_action_set.event_id:
                            event_context = EventContext(maintenance_action_set.event_id)
                            old_part = PartDefinition.query.get(old_part_id)
                            old_part_name = old_part.part_name if old_part else f"Part #{old_part_id}"
                            new_part_name = new_part.part_name
                            comment_text = f"[Part Demand Updated] Changed part from {old_part_name} to {new_part_name} by user {user_id}"
                            event_context.add_comment(
                                user_id=user_id,
                                content=comment_text,
                                is_human_made=False
                            )
                            db.session.commit()
                except Exception as e:
                    logger.warning(f"Could not add comment for part ID change: {e}")
                
                success_count += 1
            except Exception as e:
                failure_count += 1
                errors.append(f"Part demand {part_demand_id}: {str(e)}")
                logger.error(f"Error changing part ID for part demand {part_demand_id}: {e}")
                db.session.rollback()
        
        return {
            'success': True,
            'success_count': success_count,
            'failure_count': failure_count,
            'errors': errors,
            'message': f'Changed part ID for {success_count} part demand(s), {failure_count} failed'
        }
    
    @staticmethod
    def cancel_part_demand(part_demand_id: int, user_id: int, reason: str) -> Dict[str, Any]:
        """
        Cancel a part demand (manager cancellation).
        
        Args:
            part_demand_id: Part demand ID to cancel
            user_id: User ID cancelling
            reason: Cancellation reason (required)
            
        Returns:
            Dict with success status and message
            
        Raises:
            ValueError: If part demand not found or not in valid status
        """
        if not reason or not reason.strip():
            raise ValueError("Cancellation reason is required")
        
        part_demand = PartDemand.query.get(part_demand_id)
        if not part_demand:
            raise ValueError(f"Part demand {part_demand_id} not found")
        
        # Prevent operations on items that are already Issued, Ordered, or Installed
        blocked_statuses = ['Issued', 'Ordered', 'Installed']
        if part_demand.status in blocked_statuses:
            raise ValueError(f"Cannot cancel part demand in status '{part_demand.status}'. This item has already been processed.")
        
        # Allow cancellation for Pending Inventory Approval and Pending Manager Approval
        valid_statuses = ['Pending Inventory Approval', 'Pending Manager Approval', 'Planned', 'Requested']
        if part_demand.status not in valid_statuses:
            raise ValueError(f"Cannot cancel part demand in status '{part_demand.status}'. Must be one of: {', '.join(valid_statuses)}")
        
        # Update status
        part_demand.status = 'Cancelled by Manager'
        if hasattr(part_demand, 'notes'):
            existing_notes = part_demand.notes or ''
            part_demand.notes = f"{existing_notes}\n[Cancelled by manager {user_id}] {reason}".strip()
        
        db.session.commit()
        
        # Generate automated comment
        try:
            action = Action.query.get(part_demand.action_id)
            if action and action.maintenance_action_set_id:
                maintenance_action_set = MaintenanceActionSet.query.get(action.maintenance_action_set_id)
                if maintenance_action_set and maintenance_action_set.event_id:
                    event_context = EventContext(maintenance_action_set.event_id)
                    part = PartDefinition.query.get(part_demand.part_id)
                    part_name = part.part_name if part else f"Part #{part_demand.part_id}"
                    comment_text = f"[Part Demand Cancelled] Cancelled part demand: {part_name} x{part_demand.quantity_required} by user {user_id}. Reason: {reason}"
                    event_context.add_comment(
                        user_id=user_id,
                        content=comment_text,
                        is_human_made=False
                    )
                    db.session.commit()
        except Exception as e:
            logger.warning(f"Could not add comment for part demand cancellation: {e}")
        
        return {'success': True, 'message': 'Part demand cancelled successfully'}




