from app.data.core.user_created_base import UserCreatedBase
from app.data.core.event_info.attachment import VirtualAttachmentReference
from app import db
from datetime import datetime
from sqlalchemy.orm import foreign

class Comment(UserCreatedBase):
    __tablename__ = 'comments'
    
    # Comment content
    content = db.Column(db.Text, nullable=False)
    
    # Relationships
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    
    # Comment properties
    is_private = db.Column(db.Boolean, default=False)  # For internal notes
    is_edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime, nullable=True)
    edited_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_human_made = db.Column(db.Boolean, default=False)  # True for manually inserted comments, False for machine-generated
    
    # Relationships
    event = db.relationship('Event', backref='comments')
    edited_by = db.relationship('User', foreign_keys=[edited_by_id])
    
    def mark_as_edited(self, edited_by_id):
        """Mark comment as edited"""
        self.is_edited = True
        self.edited_at = datetime.utcnow()
        self.edited_by_id = edited_by_id
    
    def get_content_preview(self, max_length=100):
        """Get a preview of the comment content"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
    
    def __repr__(self):
        preview = self.get_content_preview(50)
        return f'<Comment {self.id}: {preview}>'


class CommentAttachment(VirtualAttachmentReference):
    __tablename__ = 'comment_attachments'
    
    # Define attached_to_id with proper foreign key for comments
    attached_to_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    
    # Relationships
    attachment = db.relationship('Attachment')
    comment = db.relationship('Comment', backref='comment_attachments')
    
    def __init__(self, *args, **kwargs):
        """Initialize comment attachment with proper virtual reference setup"""
        # Set the attached_to_type for comment attachments
        kwargs['attached_to_type'] = 'Comment'
        super().__init__(*args, **kwargs)
    
    def __repr__(self):
        return f'<CommentAttachment Comment:{self.attached_to_id} -> Attachment:{self.attachment_id}>' 