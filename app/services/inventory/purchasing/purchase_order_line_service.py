"""
Purchase Order Line Service
Service for building queries and retrieving data for purchase order line viewing.
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from flask_sqlalchemy.pagination import Pagination
from sqlalchemy import or_, and_, exists, select, func
from sqlalchemy.orm import Query, joinedload
from app import db
from app.data.inventory.ordering.purchase_order_line import PurchaseOrderLine
from app.data.inventory.ordering.purchase_order_header import PurchaseOrderHeader
from app.data.inventory.ordering.part_demand_purchase_order_line import PartDemandPurchaseOrderLink
from app.data.maintenance.base.part_demands import PartDemand
from app.data.maintenance.base.actions import Action
from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
from app.data.core.supply.part_definition import PartDefinition
from app.data.core.user_info.user import User


class PurchaseOrderLineService:
    """
    Service for purchase order line portal presentation operations.
    Handles query building, filtering, and enhanced data retrieval.
    """
    
    @staticmethod
    def build_po_lines_query(
        # PO Line filters
        status: Optional[str] = None,
        part_number: Optional[str] = None,
        part_name: Optional[str] = None,
        
        # PO Header filters
        vendor: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        created_by_id: Optional[int] = None,
        
        # Part Demand filters
        part_demand_assigned_to_id: Optional[int] = None,
        
        # Event filters (via part demand -> action -> maintenance action set -> event)
        event_assigned_to_id: Optional[int] = None,
        asset_id: Optional[int] = None,
        
        # Search
        search_term: Optional[str] = None,
        
        # Ordering
        order_by: str = 'created_at',
        order_direction: str = 'desc'
    ) -> Query:
        """
        Build a SQLAlchemy query for purchase order lines with all filters applied.
        
        Returns:
            SQLAlchemy Query object ready for pagination
        """
        query = PurchaseOrderLine.query
        
        # ============================================================================
        # BASE FILTERS - Direct fields in PurchaseOrderLine
        # ============================================================================
        
        # Status filter
        if status:
            query = query.filter(PurchaseOrderLine.status == status)
        
        # ============================================================================
        # JOINED FILTERS - Require joins to related tables
        # ============================================================================
        
        # Part filters (via PartDefinition)
        if part_number or part_name:
            query = query.join(PartDefinition, PurchaseOrderLine.part_id == PartDefinition.id)
            if part_number:
                query = query.filter(PartDefinition.part_number.ilike(f'%{part_number}%'))
            if part_name:
                query = query.filter(PartDefinition.part_name.ilike(f'%{part_name}%'))
        
        # PO Header filters (via PurchaseOrderHeader)
        if vendor or date_from or date_to or created_by_id:
            query = query.join(PurchaseOrderHeader, PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            if vendor:
                query = query.filter(PurchaseOrderHeader.vendor_name.ilike(f'%{vendor}%'))
            if date_from:
                query = query.filter(PurchaseOrderHeader.order_date >= date_from)
            if date_to:
                query = query.filter(PurchaseOrderHeader.order_date <= date_to)
            if created_by_id:
                query = query.filter(PurchaseOrderHeader.created_by_id == created_by_id)
        
        # Part Demand assigned_to filter (via Action)
        if part_demand_assigned_to_id:
            # Join through: PurchaseOrderLine -> PartDemandPurchaseOrderLink -> PartDemand -> Action
            part_demand_subq = (
                select(1)
                .select_from(PartDemandPurchaseOrderLink)
                .join(PartDemand, PartDemandPurchaseOrderLink.part_demand_id == PartDemand.id)
                .join(Action, PartDemand.action_id == Action.id)
                .where(
                    PartDemandPurchaseOrderLink.purchase_order_line_id == PurchaseOrderLine.id,
                    Action.assigned_user_id == part_demand_assigned_to_id
                )
            )
            query = query.filter(exists(part_demand_subq))
        
        # Event filters (via PartDemand -> Action -> MaintenanceActionSet)
        if event_assigned_to_id or asset_id:
            # Join through: PurchaseOrderLine -> PartDemandPurchaseOrderLink -> PartDemand -> Action -> MaintenanceActionSet
            event_subq = (
                select(1)
                .select_from(PartDemandPurchaseOrderLink)
                .join(PartDemand, PartDemandPurchaseOrderLink.part_demand_id == PartDemand.id)
                .join(Action, PartDemand.action_id == Action.id)
                .join(MaintenanceActionSet, Action.maintenance_action_set_id == MaintenanceActionSet.id)
                .where(
                    PartDemandPurchaseOrderLink.purchase_order_line_id == PurchaseOrderLine.id
                )
            )
            
            if event_assigned_to_id:
                event_subq = event_subq.where(MaintenanceActionSet.assigned_user_id == event_assigned_to_id)
            
            if asset_id:
                event_subq = event_subq.where(MaintenanceActionSet.asset_id == asset_id)
            
            query = query.filter(exists(event_subq))
        
        # Search term (searches in part number, part name, vendor, PO number)
        if search_term:
            # Need to join PartDefinition and PurchaseOrderHeader for search
            if not (part_number or part_name):
                query = query.join(PartDefinition, PurchaseOrderLine.part_id == PartDefinition.id)
            if not (vendor or date_from or date_to or created_by_id):
                query = query.join(PurchaseOrderHeader, PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            
            query = query.filter(
                or_(
                    PartDefinition.part_number.ilike(f'%{search_term}%'),
                    PartDefinition.part_name.ilike(f'%{search_term}%'),
                    PurchaseOrderHeader.vendor_name.ilike(f'%{search_term}%'),
                    PurchaseOrderHeader.po_number.ilike(f'%{search_term}%')
                )
            )
        
        # ============================================================================
        # ORDERING
        # ============================================================================
        
        # Handle ordering
        if order_by == 'part_number':
            if not (part_number or part_name):
                query = query.join(PartDefinition, PurchaseOrderLine.part_id == PartDefinition.id)
            order_col = PartDefinition.part_number
        elif order_by == 'part_name':
            if not (part_number or part_name):
                query = query.join(PartDefinition, PurchaseOrderLine.part_id == PartDefinition.id)
            order_col = PartDefinition.part_name
        elif order_by == 'vendor':
            if not (vendor or date_from or date_to or created_by_id):
                query = query.join(PurchaseOrderHeader, PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            order_col = PurchaseOrderHeader.vendor_name
        elif order_by == 'order_date':
            if not (vendor or date_from or date_to or created_by_id):
                query = query.join(PurchaseOrderHeader, PurchaseOrderLine.purchase_order_id == PurchaseOrderHeader.id)
            order_col = PurchaseOrderHeader.order_date
        elif order_by == 'status':
            order_col = PurchaseOrderLine.status
        else:  # Default: created_at
            order_col = PurchaseOrderLine.created_at
        
        if order_direction == 'asc':
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())
        
        return query
    
    @staticmethod
    def get_po_lines_with_enhanced_data(
        query: Query,
        page: int = 1,
        per_page: int = 20
    ) -> Pagination:
        """
        Get paginated purchase order lines with enhanced relationship data.
        
        Args:
            query: SQLAlchemy query object
            page: Page number
            per_page: Items per page
            
        Returns:
            Pagination object with enhanced PO line data
        """
        # Eager load relationships to avoid N+1 queries
        # Note: part_demands is a dynamic relationship, so we can't eager load it
        query = query.options(
            joinedload(PurchaseOrderLine.purchase_order).joinedload(PurchaseOrderHeader.major_location),
            joinedload(PurchaseOrderLine.part)
        )
        
        return query.paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def get_po_line_by_id(po_line_id: int) -> Optional[PurchaseOrderLine]:
        """
        Get a single purchase order line by ID with all relationships loaded.
        
        Args:
            po_line_id: Purchase order line ID
            
        Returns:
            PurchaseOrderLine instance or None
        """
        # Note: part_demands and part_arrivals are dynamic relationships, so we can't eager load them
        return PurchaseOrderLine.query.options(
            joinedload(PurchaseOrderLine.purchase_order).joinedload(PurchaseOrderHeader.major_location),
            joinedload(PurchaseOrderLine.part)
        ).filter_by(id=po_line_id).first()
    
    @staticmethod
    def get_filter_options() -> Dict[str, Any]:
        """
        Get filter options for dropdowns.
        
        Returns:
            Dictionary with filter option lists
        """
        return {
            'statuses': ['Pending', 'Ordered', 'Shipped', 'Complete', 'Cancelled'],
            'users': User.query.filter_by(is_active=True).order_by(User.username).all(),
            'parts': PartDefinition.query.filter_by(status='Active').order_by(PartDefinition.part_number).all(),
        }
    
    @staticmethod
    def get_active_filters(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get list of active filters for display.
        
        Args:
            filters: Dictionary of filter parameters
            
        Returns:
            List of active filter dictionaries with label and value
        """
        active = []
        
        if filters.get('status'):
            active.append({'label': 'Status', 'value': filters['status']})
        
        if filters.get('part_number'):
            active.append({'label': 'Part Number', 'value': filters['part_number']})
        
        if filters.get('part_name'):
            active.append({'label': 'Part Name', 'value': filters['part_name']})
        
        if filters.get('vendor'):
            active.append({'label': 'Vendor', 'value': filters['vendor']})
        
        if filters.get('date_from'):
            active.append({'label': 'Date From', 'value': str(filters['date_from'])})
        
        if filters.get('date_to'):
            active.append({'label': 'Date To', 'value': str(filters['date_to'])})
        
        if filters.get('created_by_id'):
            user = User.query.get(filters['created_by_id'])
            if user:
                active.append({'label': 'Created By', 'value': user.username})
        
        if filters.get('part_demand_assigned_to_id'):
            user = User.query.get(filters['part_demand_assigned_to_id'])
            if user:
                active.append({'label': 'Part Demand Assigned To', 'value': user.username})
        
        if filters.get('event_assigned_to_id'):
            user = User.query.get(filters['event_assigned_to_id'])
            if user:
                active.append({'label': 'Event Assigned To', 'value': user.username})
        
        if filters.get('asset_id'):
            from app.data.core.asset_info.asset import Asset
            asset = Asset.query.get(filters['asset_id'])
            if asset:
                active.append({'label': 'Asset', 'value': asset.name})
        
        if filters.get('search_term'):
            active.append({'label': 'Search', 'value': filters['search_term']})
        
        return active






