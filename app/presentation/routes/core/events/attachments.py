from flask import Blueprint, request, send_file, flash, redirect, url_for, jsonify, render_template
from app.logger import get_logger
from flask_login import login_required, current_user
from app import db
from app.data.core.event_info.attachment import Attachment
from app.data.core.event_info.event import Event
from werkzeug.utils import secure_filename
import io
import os

bp = Blueprint('attachments', __name__)
logger = get_logger("asset_management.routes.bp")


@bp.route('/attachments/<int:attachment_id>/download')
@login_required
def download(attachment_id):
    """Download an attachment"""
    attachment = Attachment.query.get_or_404(attachment_id)

    # Get file data
    file_data = attachment.get_file_data()
    if not file_data:
        flash('File not found', 'error')
        return redirect(url_for('events.detail', event_id=attachment.event_id))

    # Create file-like object
    file_stream = io.BytesIO(file_data)
    file_stream.seek(0)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name=attachment.filename,
        mimetype=attachment.mime_type,
    )


@bp.route('/attachments/<int:attachment_id>/view')
@login_required
def view(attachment_id):
    """View an attachment in browser (for images, PDFs, text files, etc.)"""
    attachment = Attachment.query.get_or_404(attachment_id)

    # Get file data
    file_data = attachment.get_file_data()
    if not file_data:
        flash('File not found', 'error')
        return redirect(url_for('events.detail', event_id=attachment.event_id))

    # Create file-like object
    file_stream = io.BytesIO(file_data)
    file_stream.seek(0)

    # For text files, ensure proper content type for browser display
    if attachment.is_viewable_as_text():
        # Set text/plain for better browser handling of text files
        mimetype = 'text/plain'
    else:
        mimetype = attachment.mime_type

    return send_file(
        file_stream,
        mimetype=mimetype,
    )


@bp.route('/attachments/<int:attachment_id>/delete', methods=['POST'])
@login_required
def delete(attachment_id):
    """Delete an attachment"""
    attachment = Attachment.query.get_or_404(attachment_id)

    # Check if user can delete this attachment
    if attachment.created_by_id != current_user.id:
        flash('You can only delete your own attachments', 'error')
        return redirect(url_for('events.detail', event_id=attachment.event_id))

    # Find the comment that contains this attachment
    from app.data.core.event_info.comment import CommentAttachment

    comment_attachment = CommentAttachment.query.filter_by(attachment_id=attachment_id).first()

    if not comment_attachment:
        flash('Attachment not found in any comment', 'error')
        return redirect(url_for('events.list'))

    event_id = comment_attachment.comment.event_id

    # Delete file from storage
    attachment.delete_file()

    # Delete comment attachment link
    db.session.delete(comment_attachment)

    # Delete attachment
    db.session.delete(attachment)
    db.session.commit()

    flash(f'Attachment "{attachment.filename}" deleted successfully', 'success')
    return redirect(url_for('events.detail', event_id=event_id))


@bp.route('/attachments/<int:attachment_id>/info')
@login_required
def info(attachment_id):
    """Get attachment information"""
    attachment = Attachment.query.get_or_404(attachment_id)

    return jsonify(
        {
            'id': attachment.id,
            'filename': attachment.filename,
            'file_size': attachment.file_size,
            'file_size_display': attachment.get_file_size_display(),
            'mime_type': attachment.mime_type,
            'description': attachment.description,
            'tags': attachment.tags,
            'storage_type': attachment.storage_type,
            'is_image': attachment.is_image(),
            'is_document': attachment.is_document(),
            'is_viewable_as_text': attachment.is_viewable_as_text(),
            'file_icon': attachment.get_file_icon(),
            'created_at': attachment.created_at.isoformat(),
            'created_by': attachment.created_by.username if attachment.created_by else 'System',
        }
    )


@bp.route('/attachments/<int:attachment_id>/preview')
@login_required
def preview(attachment_id):
    """Get text preview of attachment (first 10 lines or full content for small files)"""
    attachment = Attachment.query.get_or_404(attachment_id)

    if not attachment.is_viewable_as_text():
        return render_template('attachments/preview.html', preview=None, attachment_id=attachment_id)

    # Get file data
    file_data = attachment.get_file_data()
    if not file_data:
        return render_template('attachments/preview.html', preview=None, attachment_id=attachment_id)

    try:
        # Decode text content
        content = file_data.decode('utf-8')
        lines = content.split('\n')

        # Always return first 10 lines
        preview_lines = lines[:10]
        preview_content = '\n'.join(preview_lines)
        return render_template(
            'attachments/preview.html',
            preview=preview_content,
            is_full=False,
            line_count=len(lines),
            preview_lines=len(preview_lines),
            attachment_id=attachment_id,
        )

    except UnicodeDecodeError:
        return render_template('attachments/preview.html', preview=None, attachment_id=attachment_id)


