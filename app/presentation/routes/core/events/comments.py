from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from app.logger import get_logger
from flask_login import login_required, current_user
from app import db
from app.data.core.event_info.comment import Comment
from app.data.core.event_info.event import Event
from app.buisness.core.event_context import EventContext
from app.services.core.event_service import EventService
import json

bp = Blueprint('comments', __name__)
logger = get_logger("asset_management.routes.bp")


@bp.route('/events/<int:event_id>/comments', methods=['POST'])
@login_required
def create(event_id):
    """Create a new comment on an event"""
    event_context = EventContext(event_id)

    content = request.form.get('content', '').strip()
    is_private = request.form.get('is_private') == 'on'

    # Get files if any
    files = request.files.getlist('attachments')
    has_files = any(file and file.filename for file in files)

    try:
        if has_files:
            # Use EventContext to handle comment with attachments (auto_commit=True handles transaction)
            event_context.add_comment_with_attachments(
                user_id=current_user.id,
                content=content,
                file_objects=files,
                is_private=is_private,
                is_human_made=True,  # Comments created via UI are human-made
                auto_commit=True
            )
        else:
            # Simple comment without attachments
            if not content:
                flash('Comment content is required', 'error')
                return redirect(url_for('events.detail', event_id=event_id))
            
            event_context.add_comment(
                user_id=current_user.id,
                content=content,
                is_private=is_private,
                is_human_made=True  # Comments created via UI are human-made
            )
            db.session.commit()

        # If this is an HTMX request, return the updated event widget instead of redirecting
        if request.headers.get('HX-Request'):
            event_context.refresh()  # Refresh to get latest comments
            # Preserve filter state if it was set
            filter_human_only = request.args.get('human_only', 'false').lower() == 'true'
            if filter_human_only:
                # Use service for presentation-specific filtering
                comments = EventService.get_human_comments(event_id)
            else:
                comments = event_context.comments
            return render_template(
                'components/event_widget.html',
                event=event_context.event,
                comments=comments,
                filter_human_only=filter_human_only,
            )

        flash('Comment added successfully', 'success')
        return redirect(url_for('events.detail', event_id=event_id))
    
    except ValueError as e:
        flash(str(e), 'error')
        db.session.rollback()
        return redirect(url_for('events.detail', event_id=event_id))


@bp.route('/events/<int:event_id>/widget', methods=['GET'])
@login_required
def event_widget(event_id):
    """
    Render the reusable Event widget (comments, attachments, metadata)
    for the given event. Intended for embedding via HTMX on any page.
    """
    event_context = EventContext(event_id)
    
    # Check if filtering to human comments only
    filter_human_only = request.args.get('human_only', 'false').lower() == 'true'
    
    if filter_human_only:
        # Use service for presentation-specific filtering
        comments = EventService.get_human_comments(event_id)
    else:
        comments = event_context.comments

    return render_template(
        'components/event_widget.html',
        event=event_context.event,
        comments=comments,
        filter_human_only=filter_human_only,
    )


# ROUTE_TYPE: SIMPLE_CRUD (EDIT)
# EXCEPTION: Direct ORM usage allowed for simple EDIT operations on Comment
# This route performs basic update operations with minimal business logic.
# Rationale: Simple comment edit doesn't require domain abstraction.
# NOTE: CREATE/DELETE operations should use domain managers - see create() and delete() routes
@bp.route('/comments/<int:comment_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(comment_id):
    """Edit an existing comment"""
    comment = Comment.query.get_or_404(comment_id)

    # Check if user can edit this comment
    if comment.created_by_id != current_user.id:
        flash('You can only edit your own comments', 'error')
        return redirect(url_for('events.detail', event_id=comment.event_id))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        is_private = request.form.get('is_private') == 'on'

        if not content:
            flash('Comment content is required', 'error')
            return redirect(url_for('events.detail', event_id=comment.event_id))

        # Update comment
        comment.content = content
        comment.is_private = is_private
        comment.mark_as_edited(current_user.id)
        comment.updated_by_id = current_user.id

        db.session.commit()
        flash('Comment updated successfully', 'success')

        return redirect(url_for('events.detail', event_id=comment.event_id))

    # GET request - return comment data for AJAX
    return jsonify(
        {
            'id': comment.id,
            'content': comment.content,
            'is_private': comment.is_private,
        }
    )


@bp.route('/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete(comment_id):
    """Delete a comment"""
    comment = Comment.query.get_or_404(comment_id)

    # Check if user can delete this comment
    if comment.created_by_id != current_user.id:
        return jsonify({'error': 'You can only delete your own comments'}), 403

    event_id = comment.event_id

    # Delete associated comment attachments and files
    for comment_attachment in comment.comment_attachments:
        attachment = comment_attachment.attachment
        attachment.delete_file()  # Delete from filesystem if needed
        db.session.delete(attachment)
        db.session.delete(comment_attachment)

    # Delete the comment
    db.session.delete(comment)
    db.session.commit()

    if request.headers.get('Content-Type') == 'application/json':
        return jsonify({'success': True})

    flash('Comment deleted successfully', 'success')
    return redirect(url_for('events.detail', event_id=event_id))


