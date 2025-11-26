"""
Event management routes
CRUD operations for Event model
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from app.logger import get_logger
from flask_login import login_required, current_user
from app.data.core.event_info.event import Event
from app.data.core.asset_info.asset import Asset
from app.data.core.major_location import MajorLocation
from app.services.core.event_service import EventService
from app import db

bp = Blueprint('events', __name__)
logger = get_logger("asset_management.routes.bp")

@bp.route('/events')
@login_required
def list():
    """List all events with optional condensed view"""
    condensed_view = request.args.get('condensed-view', False, type=bool)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('row_count', 20, type=int)

    if condensed_view:
        page, per_page = 1, 10

    # Use service to get list data
    events, filters = EventService.get_list_data(
        request=request,
        page=page,
        per_page=per_page
    )

    # Get filter options from service
    filter_options = EventService.get_filter_options()

    # Choose template based on view type
    template = 'core/events/recent_events/recent_events.html' if condensed_view else 'core/events/list.html'

    return render_template(
        template,
        events=events,
        users=filter_options['users'],
        assets=filter_options['assets'],
        locations=filter_options['locations'],
        make_models=filter_options['make_models'],
        filters=filters,
    )


@bp.route('/events/<int:event_id>')
@login_required
def detail(event_id):
    """View event details using EventContext"""
    from app.buisness.core.event_context import EventContext
    event_context = EventContext(event_id)

    return render_template('core/events/detail.html', 
                         event=event_context.event,
                         comments=event_context.comments,
                         attachments=event_context.attachments)


@bp.route('/events/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new event"""
    if request.method == 'POST':
        # Validate form data
        event_type = request.form.get('event_type')
        description = request.form.get('description')
        asset_id = request.form.get('asset_id', type=int)
        major_location_id = request.form.get('major_location_id', type=int)

        # Validate required fields
        if not event_type or not description:
            flash('Event type and description are required', 'error')
            filter_options = EventService.get_filter_options()
            return render_template(
                'core/events/create.html',
                assets=filter_options['assets'],
                locations=filter_options['locations'],
            )

        # Create new event
        event = Event(
            event_type=event_type,
            description=description,
            user_id=current_user.id,
            asset_id=asset_id,
            major_location_id=major_location_id,
        )

        db.session.add(event)
        db.session.commit()

        flash('Event created successfully', 'success')
        return redirect(url_for('events.detail', event_id=event.id))

    # Get form options from service
    filter_options = EventService.get_filter_options()

    return render_template(
        'core/events/create.html',
        assets=filter_options['assets'],
        locations=filter_options['locations'],
    )


# ROUTE_TYPE: SIMPLE_CRUD (EDIT)
# EXCEPTION: Direct ORM usage allowed for simple EDIT operations on Event
# This route performs basic update operations with minimal business logic.
# Rationale: Simple event update doesn't require domain abstraction.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(event_id):
    """Edit event"""
    event = Event.query.get_or_404(event_id)

    if request.method == 'POST':
        # Validate form data
        event_type = request.form.get('event_type')
        description = request.form.get('description')
        asset_id = request.form.get('asset_id', type=int)
        major_location_id = request.form.get('major_location_id', type=int)

        # Update event
        event.event_type = event_type
        event.description = description
        event.asset_id = asset_id
        event.major_location_id = major_location_id

        db.session.commit()

        flash('Event updated successfully', 'success')
        return redirect(url_for('events.detail', event_id=event.id))

    # Get form options from service
    filter_options = EventService.get_filter_options()

    return render_template(
        'core/events/edit.html',
        event=event,
        assets=filter_options['assets'],
        locations=filter_options['locations'],
    )


@bp.route('/events/<int:event_id>/delete', methods=['POST'])
@login_required
def delete(event_id):
    """Delete event"""
    event = Event.query.get_or_404(event_id)

    db.session.delete(event)
    db.session.commit()

    flash('Event deleted successfully', 'success')
    return redirect(url_for('events.list'))


@bp.route('/events/card')
@login_required
def events_card():
    """HTMX endpoint for events card"""
    condensed_view = request.args.get('condensed-view', False, type=bool)

    # Use service to get card data
    events, filters = EventService.get_card_data(
        request=request,
        condensed_view=condensed_view
    )

    if condensed_view:
        return render_template(
            'core/events/recent_events/recent_events_card.html',
            events=events,
            filters=filters,
        )
    else:
        return render_template(
            'core/events/events_card.html',
            events=events,
            filters=filters,
        )


