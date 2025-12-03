"""
Create & Assign Portal Routes
Routes for creating maintenance events from templates and assigning them to technicians
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from app.logger import get_logger
from app.services.maintenance.assign_monitor_service import AssignMonitorService
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.major_location import MajorLocation
from app.data.core.user_info.user import User

logger = get_logger("asset_management.routes.maintenance.manager.create_assign")

# Use the existing manager_bp from main.py
from app.presentation.routes.maintenance.user_views.manager.main import manager_bp


@manager_bp.route('/create-assign')
@login_required
def create_assign():
    """
    Main create & assign portal page.
    Displays create event form with template selection, asset selection, and assignment options.
    """
    logger.info(f"Create & Assign portal accessed by {current_user.username}")
    
    try:
        # Get templates and technicians for form
        templates, _ = AssignMonitorService.get_active_templates()
        technicians, _ = AssignMonitorService.get_available_technicians()
        
        # Get filter options for dropdowns
        asset_types = AssetType.query.filter_by(is_active=True).order_by(AssetType.name).all()
        make_models = MakeModel.query.filter_by(is_active=True).order_by(MakeModel.make, MakeModel.model).all()
        locations = MajorLocation.query.order_by(MajorLocation.name).all()
        
        return render_template(
            'maintenance/user_views/manager/create_assign.html',
            templates=templates,
            technicians=technicians,
            asset_types=asset_types,
            make_models=make_models,
            locations=locations,
        )
    except Exception as e:
        logger.error(f"Error loading create & assign portal: {e}")
        flash('Error loading portal. Please try again.', 'error')
        return redirect(url_for('manager_portal.dashboard'))


@manager_bp.route('/create-assign/create', methods=['GET', 'POST'])
@login_required
def create_event():
    """
    Create maintenance event from template.
    GET: Show creation form
    POST: Process creation and redirect back to portal homepage
    """
    if request.method == 'GET':
        # Get form data
        template_id = request.args.get('template_id', type=int)
        
        try:
            templates, _ = AssignMonitorService.get_active_templates()
            technicians, _ = AssignMonitorService.get_available_technicians()
            asset_types = AssetType.query.filter_by(is_active=True).order_by(AssetType.name).all()
            make_models = MakeModel.query.filter_by(is_active=True).order_by(MakeModel.make, MakeModel.model).all()
            locations = MajorLocation.query.order_by(MajorLocation.name).all()
            
            template_summary = None
            if template_id:
                template_summary = AssignMonitorService.get_template_summary(template_id)
            
            return render_template(
                'maintenance/user_views/manager/create_event.html',
                templates=templates,
                technicians=technicians,
                asset_types=asset_types,
                make_models=make_models,
                locations=locations,
                selected_template_id=template_id,
                template_summary=template_summary,
            )
        except Exception as e:
            logger.error(f"Error loading create event form: {e}")
            flash('Error loading form. Please try again.', 'error')
            return redirect(url_for('manager_portal.create_assign'))
    
    # POST: Process form submission
    try:
        # Get form data
        template_action_set_id = request.form.get('template_id', type=int)
        asset_id = request.form.get('asset_id', type=int)
        assigned_user_id = request.form.get('assigned_user_id', type=int) or None
        priority = request.form.get('priority')
        notes = request.form.get('notes', '').strip() or None
        
        # Get planned start datetime
        planned_start_str = request.form.get('planned_start_datetime')
        planned_start_datetime = None
        if planned_start_str:
            try:
                planned_start_datetime = datetime.fromisoformat(planned_start_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Validate required fields
        if not template_action_set_id:
            flash('Template is required', 'error')
            return redirect(url_for('manager_portal.create_event'))
        
        if not asset_id:
            flash('Asset is required', 'error')
            return redirect(url_for('manager_portal.create_event'))
        
        if not planned_start_datetime:
            flash('Planned Start Date/Time is required', 'error')
            return redirect(url_for('manager_portal.create_event'))
        
        if not priority:
            flash('Priority is required', 'error')
            return redirect(url_for('manager_portal.create_event'))
        
        # Validate assigned_user_id if provided
        if assigned_user_id is not None:
            user = User.query.filter_by(id=assigned_user_id, is_active=True).first()
            if not user:
                flash(f'Invalid technician: User ID {assigned_user_id} not found or inactive', 'error')
                return redirect(url_for('manager_portal.create_event'))
        
        # Create event
        maintenance_action_set = AssignMonitorService.create_event_from_template(
            template_action_set_id=template_action_set_id,
            asset_id=asset_id,
            planned_start_datetime=planned_start_datetime,
            user_id=current_user.id,
            assigned_user_id=assigned_user_id,
            assigned_by_id=current_user.id if assigned_user_id else None,
            priority=priority,
            notes=notes
        )
        
        flash(
            f'Maintenance event {maintenance_action_set.id} created successfully!',
            'success'
        )
        
        # Redirect back to portal homepage
        return redirect(url_for('manager_portal.create_assign'))
        
    except ValueError as e:
        logger.warning(f"Validation error creating event: {e}")
        flash(str(e), 'error')
        return redirect(url_for('manager_portal.create_event'))
    except Exception as e:
        logger.error(f"Error creating maintenance event: {e}")
        flash('Error creating maintenance event. Please try again.', 'error')
        return redirect(url_for('manager_portal.create_event'))


@manager_bp.route('/create-assign/unassigned')
@login_required
def unassigned_events():
    """
    View unassigned maintenance events with filtering options.
    Displays list of events where assigned_user_id is None.
    """
    logger.info(f"Unassigned events page accessed by {current_user.username}")
    
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Get filter parameters
        asset_id = request.args.get('asset_id', type=int)
        asset_type_id = request.args.get('asset_type_id', type=int)
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        # Get date range filters
        date_from_str = request.args.get('date_from')
        date_to_str = request.args.get('date_to')
        date_from = None
        date_to = None
        
        if date_from_str:
            try:
                date_from = datetime.fromisoformat(date_from_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        if date_to_str:
            try:
                date_to = datetime.fromisoformat(date_to_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
        
        # Get unassigned events with pagination
        events = AssignMonitorService.get_unassigned_events(
            asset_id=asset_id,
            asset_type_id=asset_type_id,
            status=status,
            priority=priority,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page
        )
        
        # Get filter options
        technicians, _ = AssignMonitorService.get_available_technicians()
        asset_types = AssetType.query.filter_by(is_active=True).order_by(AssetType.name).all()
        
        return render_template(
            'maintenance/user_views/manager/unassigned_events.html',
            events=events,
            technicians=technicians,
            asset_types=asset_types,
            current_filters={
                'asset_id': asset_id,
                'asset_type_id': asset_type_id,
                'status': status,
                'priority': priority,
                'date_from': date_from_str,
                'date_to': date_to_str,
            }
        )
    except Exception as e:
        logger.error(f"Error loading unassigned events: {e}", exc_info=True)
        flash(f'Error loading unassigned events: {str(e)}', 'error')
        return redirect(url_for('manager_portal.create_assign'))


@manager_bp.route('/create-assign/unassigned/bulk-assign', methods=['POST'])
@login_required
def bulk_assign_events():
    """
    Bulk assign multiple unassigned events to a technician.
    Processes selected events and assigns them all to the chosen technician.
    """
    try:
        # Get form data
        event_ids_str = request.form.get('event_ids', '')
        assigned_user_id = request.form.get('assigned_user_id', type=int)
        notes = request.form.get('notes', '').strip() or None
        
        # Validate required fields
        if not event_ids_str:
            flash('No events selected', 'error')
            return redirect(url_for('manager_portal.unassigned_events'))
        
        if not assigned_user_id:
            flash('Technician is required', 'error')
            return redirect(url_for('manager_portal.unassigned_events'))
        
        # Parse event IDs
        try:
            event_ids = [int(eid.strip()) for eid in event_ids_str.split(',') if eid.strip()]
        except ValueError:
            flash('Invalid event IDs', 'error')
            return redirect(url_for('manager_portal.unassigned_events'))
        
        if not event_ids:
            flash('No valid events selected', 'error')
            return redirect(url_for('manager_portal.unassigned_events'))
        
        # Bulk assign
        success_count, failed_count, failed_event_ids = AssignMonitorService.bulk_assign_events(
            event_ids=event_ids,
            assigned_user_id=assigned_user_id,
            assigned_by_id=current_user.id,
            notes=notes
        )
        
        # Show results
        if success_count > 0:
            flash(
                f'Successfully assigned {success_count} event(s) to technician',
                'success'
            )
        
        if failed_count > 0:
            flash(
                f'Failed to assign {failed_count} event(s). Event IDs: {", ".join(map(str, failed_event_ids))}',
                'warning'
            )
        
        # Redirect back to unassigned events list
        return redirect(url_for('manager_portal.unassigned_events'))
        
    except ValueError as e:
        logger.warning(f"Validation error in bulk assign: {e}")
        flash(str(e), 'error')
        return redirect(url_for('manager_portal.unassigned_events'))
    except Exception as e:
        logger.error(f"Error in bulk assign: {e}")
        flash('Error assigning events. Please try again.', 'error')
        return redirect(url_for('manager_portal.unassigned_events'))


# HTMX search bar endpoints
@manager_bp.route('/create-assign/search-bars/templates')
@login_required
def search_bars_templates():
    """HTMX endpoint to return template search results"""
    try:
        # Handle both filter_asset_type and asset_type_id parameter names
        asset_type_id = request.args.get('asset_type_id', type=int) or request.args.get('filter_asset_type', type=int)
        make_model_id = request.args.get('make_model_id', type=int) or request.args.get('filter_make_model', type=int)
        search = request.args.get('search', '').strip()
        limit = request.args.get('limit', type=int, default=8)
        selected_template_id = request.args.get('selected_template_id', type=int)
        
        templates, total_count = AssignMonitorService.get_active_templates(
            asset_type_id=asset_type_id,
            make_model_id=make_model_id,
            search=search if search else None,
            limit=limit
        )
        
        return render_template(
            'maintenance/user_views/manager/search_bars/templates_results.html',
            templates=templates,
            total_count=total_count,
            showing=len(templates),
            search=search,
            selected_template_id=selected_template_id
        )
    except Exception as e:
        logger.error(f"Error in templates search: {e}")
        return render_template(
            'maintenance/user_views/manager/search_bars/templates_results.html',
            templates=[],
            total_count=0,
            showing=0,
            search=search or '',
            error=str(e)
        ), 500


@manager_bp.route('/create-assign/search-bars/assets')
@login_required
def search_bars_assets():
    """HTMX endpoint to return asset search results"""
    try:
        # Handle both filter_* and direct parameter names
        asset_type_id = request.args.get('asset_type_id', type=int) or request.args.get('filter_asset_type', type=int)
        make_model_id = request.args.get('make_model_id', type=int) or request.args.get('filter_make_model', type=int)
        location_id = request.args.get('location_id', type=int) or request.args.get('filter_location', type=int)
        search = request.args.get('search', '').strip()
        limit = request.args.get('limit', type=int, default=8)
        selected_asset_id = request.args.get('selected_asset_id', type=int)
        
        assets, total_count = AssignMonitorService.get_available_assets(
            asset_type_id=asset_type_id,
            make_model_id=make_model_id,
            location_id=location_id,
            search=search if search else None,
            limit=limit
        )
        
        return render_template(
            'maintenance/user_views/manager/search_bars/assets_results.html',
            assets=assets,
            total_count=total_count,
            showing=len(assets),
            search=search,
            selected_asset_id=selected_asset_id
        )
    except Exception as e:
        logger.error(f"Error in assets search: {e}")
        return render_template(
            'maintenance/user_views/manager/search_bars/assets_results.html',
            assets=[],
            total_count=0,
            showing=0,
            search=search or '',
            error=str(e)
        ), 500


@manager_bp.route('/create-assign/search-bars/assignment')
@login_required
def search_bars_assignment():
    """HTMX endpoint to return technician/assignment search results"""
    try:
        search = request.args.get('search', '').strip()
        limit = request.args.get('limit', type=int, default=8)
        selected_technician_id = request.args.get('selected_technician_id', type=int)
        
        technicians, total_count = AssignMonitorService.get_available_technicians(
            search=search if search else None,
            limit=limit
        )
        
        return render_template(
            'maintenance/user_views/manager/search_bars/assignment_results.html',
            technicians=technicians,
            total_count=total_count,
            showing=len(technicians),
            search=search,
            selected_technician_id=selected_technician_id
        )
    except Exception as e:
        logger.error(f"Error in assignment search: {e}")
        return render_template(
            'maintenance/user_views/manager/search_bars/assignment_results.html',
            technicians=[],
            total_count=0,
            showing=0,
            search=search or '',
            error=str(e)
        ), 500


@manager_bp.route('/create-assign/api/template/<int:template_id>/summary')
@login_required
def api_template_summary(template_id):
    """API endpoint to get template summary"""
    try:
        summary = AssignMonitorService.get_template_summary(template_id)
        if summary:
            return jsonify(summary)
        else:
            return jsonify({'error': 'Template not found'}), 404
    except Exception as e:
        logger.error(f"Error in template summary API: {e}")
        return jsonify({'error': str(e)}), 500

