"""
Technician Portal Main Routes
Dashboard and main navigation for maintenance technicians
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.logger import get_logger
from app import db

logger = get_logger("asset_management.routes.maintenance.technician")

# Create technician portal blueprint
technician_bp = Blueprint('technician_portal', __name__, url_prefix='/maintenance/technician')


@technician_bp.route('/')
@technician_bp.route('/dashboard')
@login_required
def dashboard():
    """Technician dashboard with assigned work"""
    logger.info(f"Technician dashboard accessed by {current_user.username}")
    
    # Get basic stats
    stats = {
        'assigned_work': 0,
        'in_progress': 0,
        'completed_today': 0,
    }
    
    # Quick access features
    quick_access = {
        'most_recently_assigned_event': None,
        'most_recently_commented_event': None,
    }
    
    # Additional widgets data
    top_assets = []
    recent_part_demands = []
    oldest_part_demands_needing_approval = []
    oldest_part_demands_not_received = []
    most_recently_completed_location_id = None
    
    try:
        from app.data.maintenance.base.actions import Action
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from app.data.core.event_info.comment import Comment
        from app.data.core.event_info.event import Event
        from app.data.maintenance.base.part_demands import PartDemand
        from app.data.core.asset_info.asset import Asset
        from sqlalchemy import desc, func, asc
        
        # Get work assigned to current user
        stats['assigned_work'] = Action.query.filter_by(
            assigned_user_id=current_user.id
        ).filter(Action.status.in_(['Not Started', 'In Progress'])).count()
        
        stats['in_progress'] = Action.query.filter_by(
            assigned_user_id=current_user.id,
            status='In Progress'
        ).count()
        
        # Feature #1: Most Recently Assigned Event
        # Use updated_at since assigned_at doesn't exist
        most_recent_assigned = MaintenanceActionSet.query.filter_by(
            assigned_user_id=current_user.id
        ).order_by(desc(MaintenanceActionSet.updated_at)).first()
        
        if most_recent_assigned and most_recent_assigned.event_id:
            quick_access['most_recently_assigned_event'] = {
                'event_id': most_recent_assigned.event_id,
                'task_name': most_recent_assigned.task_name,
                'updated_at': most_recent_assigned.updated_at,
            }
        
        # Feature #2: Most Recently Commented On Event
        # Join Comment with Event and MaintenanceActionSet
        most_recent_comment = Comment.query.join(
            Event, Comment.event_id == Event.id
        ).join(
            MaintenanceActionSet, Event.id == MaintenanceActionSet.event_id
        ).filter(
            Comment.created_by_id == current_user.id,
            Comment.user_viewable.is_(None)  # Only visible comments
        ).order_by(desc(Comment.created_at)).first()
        
        if most_recent_comment:
            # Get the maintenance action set for this event
            maintenance_action_set = MaintenanceActionSet.query.filter_by(
                event_id=most_recent_comment.event_id
            ).first()
            
            if maintenance_action_set:
                quick_access['most_recently_commented_event'] = {
                    'event_id': most_recent_comment.event_id,
                    'task_name': maintenance_action_set.task_name,
                    'comment_created_at': most_recent_comment.created_at,
                    'comment_preview': most_recent_comment.get_content_preview(50),
                }
        
        # Feature #8: Top Five Assets with Most Actions Completed (last 6 months)
        six_months_ago = datetime.now() - timedelta(days=180)
        top_assets_query = db.session.query(
            Asset.id,
            Asset.name,
            func.count(Action.id).label('action_count')
        ).join(
            MaintenanceActionSet, Asset.id == MaintenanceActionSet.asset_id
        ).join(
            Action, MaintenanceActionSet.id == Action.maintenance_action_set_id
        ).filter(
            Action.assigned_user_id == current_user.id,
            Action.status == 'Complete',
            Action.updated_at >= six_months_ago
        ).group_by(
            Asset.id, Asset.name
        ).order_by(
            desc('action_count')
        ).limit(5).all()
        
        top_assets = [
            {'id': asset_id, 'name': name, 'action_count': count}
            for asset_id, name, count in top_assets_query
        ]
        
        # Feature #9: Ten Most Recent Part Demands with Status Updates
        recent_part_demands_query = PartDemand.query.join(
            Action, PartDemand.action_id == Action.id
        ).join(
            MaintenanceActionSet, Action.maintenance_action_set_id == MaintenanceActionSet.id
        ).filter(
            MaintenanceActionSet.assigned_user_id == current_user.id
        ).order_by(
            desc(PartDemand.updated_at)
        ).limit(10).all()
        
        recent_part_demands = []
        for pd in recent_part_demands_query:
            # Get event_id from the action's maintenance_action_set
            event_id = None
            if pd.action and pd.action.maintenance_action_set:
                event_id = pd.action.maintenance_action_set.event_id
            
            recent_part_demands.append({
                'id': pd.id,
                'part_name': pd.part.name if pd.part else 'Unknown Part',
                'quantity': pd.quantity_required,
                'status': pd.status,
                'updated_at': pd.updated_at,
                'event_id': event_id,
            })
        
        # Feature #10: Ten Oldest Part Demands Needing Approval
        oldest_part_demands_needing_approval_query = PartDemand.query.join(
            Action, PartDemand.action_id == Action.id
        ).join(
            MaintenanceActionSet, Action.maintenance_action_set_id == MaintenanceActionSet.id
        ).filter(
            MaintenanceActionSet.assigned_user_id == current_user.id,
            db.or_(
                PartDemand.status == 'Pending Manager Approval',
                PartDemand.maintenance_approval_by_id.is_(None)
            )
        ).order_by(
            asc(PartDemand.created_at)
        ).limit(10).all()
        
        oldest_part_demands_needing_approval = []
        for pd in oldest_part_demands_needing_approval_query:
            # Get event_id from the action's maintenance_action_set
            event_id = None
            if pd.action and pd.action.maintenance_action_set:
                event_id = pd.action.maintenance_action_set.event_id
            
            days_waiting = 0
            if pd.created_at:
                days_waiting = (datetime.now() - pd.created_at).days
            
            oldest_part_demands_needing_approval.append({
                'id': pd.id,
                'part_name': pd.part.name if pd.part else 'Unknown Part',
                'quantity': pd.quantity_required,
                'status': pd.status,
                'created_at': pd.created_at,
                'days_waiting': days_waiting,
                'event_id': event_id,
            })
        
        # Feature #11: Ten Oldest Not Issued/Rejected/Pending Part Demands
        # Parts that were approved but haven't been received
        statuses_not_received = ['Pending Inventory Approval', 'Ordered', 'Backordered']
        oldest_part_demands_not_received_query = PartDemand.query.join(
            Action, PartDemand.action_id == Action.id
        ).join(
            MaintenanceActionSet, Action.maintenance_action_set_id == MaintenanceActionSet.id
        ).filter(
            MaintenanceActionSet.assigned_user_id == current_user.id,
            PartDemand.status.in_(statuses_not_received)
        ).order_by(
            asc(PartDemand.created_at)
        ).limit(10).all()
        
        oldest_part_demands_not_received = []
        for pd in oldest_part_demands_not_received_query:
            # Get event_id from the action's maintenance_action_set
            event_id = None
            if pd.action and pd.action.maintenance_action_set:
                event_id = pd.action.maintenance_action_set.event_id
            
            days_waiting = 0
            if pd.created_at:
                days_waiting = (datetime.now() - pd.created_at).days
            
            oldest_part_demands_not_received.append({
                'id': pd.id,
                'part_name': pd.part.name if pd.part else 'Unknown Part',
                'quantity': pd.quantity_required,
                'status': pd.status,
                'created_at': pd.created_at,
                'days_waiting': days_waiting,
                'event_id': event_id,
            })
        
        # Get most recently completed event's major location
        most_recently_completed = MaintenanceActionSet.query.filter_by(
            assigned_user_id=current_user.id,
            status='Complete'
        ).order_by(desc(MaintenanceActionSet.updated_at)).first()
        
        if most_recently_completed and most_recently_completed.event_id:
            event = Event.query.get(most_recently_completed.event_id)
            if event and event.major_location_id:
                most_recently_completed_location_id = event.major_location_id
            elif most_recently_completed.asset and most_recently_completed.asset.major_location_id:
                most_recently_completed_location_id = most_recently_completed.asset.major_location_id
        
    except ImportError as e:
        logger.warning(f"Could not load technician stats: {e}")
    except Exception as e:
        logger.error(f"Error loading dashboard data: {e}")
        import traceback
        traceback.print_exc()
    
    # Calculate date range for "Planned This Week" (Feature #5)
    # Includes work planned in the last 7 days and the upcoming week
    today = datetime.now().date()
    start_of_week = today - timedelta(days=7)  # Last 7 days
    end_of_week = today + timedelta(days=7)    # Upcoming week (next 7 days)
    
    return render_template(
        'maintenance/user_views/technician/dashboard.html',
        stats=stats,
        quick_access=quick_access,
        start_of_week=start_of_week,
        end_of_week=end_of_week,
        top_assets=top_assets,
        recent_part_demands=recent_part_demands,
        oldest_part_demands_needing_approval=oldest_part_demands_needing_approval,
        oldest_part_demands_not_received=oldest_part_demands_not_received,
        most_recently_completed_location_id=most_recently_completed_location_id,
    )


@technician_bp.route('/most-recent-event')
@login_required
def most_recent_event():
    """Redirect to the most recently assigned event for the current user"""
    logger.info(f"Most recent event accessed by {current_user.username}")
    
    try:
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from sqlalchemy import desc
        
        # Get most recently assigned event
        most_recent_assigned = MaintenanceActionSet.query.filter_by(
            assigned_user_id=current_user.id
        ).order_by(desc(MaintenanceActionSet.updated_at)).first()
        
        if most_recent_assigned and most_recent_assigned.event_id:
            return redirect(url_for('maintenance_event_view.view_maintenance_event', event_id=most_recent_assigned.event_id))
        else:
            flash("No assigned events found.", "info")
            return redirect(url_for('technician_portal.dashboard'))
            
    except ImportError as e:
        logger.warning(f"Could not load maintenance action sets: {e}")
        flash("Error loading events.", "error")
        return redirect(url_for('technician_portal.dashboard'))
    except Exception as e:
        logger.error(f"Error finding most recent event: {e}")
        flash("Error finding most recent event.", "error")
        return redirect(url_for('technician_portal.dashboard'))


@technician_bp.route('/continue-discussion')
@login_required
def continue_discussion():
    """Redirect to the most recently commented on event for the current user"""
    logger.info(f"Continue discussion accessed by {current_user.username}")
    
    try:
        from app.data.core.event_info.comment import Comment
        from app.data.core.event_info.event import Event
        from app.data.maintenance.base.maintenance_action_sets import MaintenanceActionSet
        from sqlalchemy import desc
        
        # Get most recently commented on event
        most_recent_comment = Comment.query.join(
            Event, Comment.event_id == Event.id
        ).join(
            MaintenanceActionSet, Event.id == MaintenanceActionSet.event_id
        ).filter(
            Comment.created_by_id == current_user.id,
            Comment.user_viewable.is_(None)  # Only visible comments
        ).order_by(desc(Comment.created_at)).first()
        
        if most_recent_comment and most_recent_comment.event_id:
            return redirect(url_for('maintenance_event_view.view_maintenance_event', event_id=most_recent_comment.event_id))
        else:
            flash("No commented events found.", "info")
            return redirect(url_for('technician_portal.dashboard'))
            
    except ImportError as e:
        logger.warning(f"Could not load comment modules: {e}")
        flash("Error loading events.", "error")
        return redirect(url_for('technician_portal.dashboard'))
    except Exception as e:
        logger.error(f"Error finding most recent comment: {e}")
        flash("Error finding most recent comment.", "error")
        return redirect(url_for('technician_portal.dashboard'))

