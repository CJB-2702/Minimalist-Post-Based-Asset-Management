from app.data.core.user_created_base import UserCreatedBase
from app.data.core.event_info.attachment import VirtualAttachmentReference
from app import db
from sqlalchemy.orm import foreign

class Comment(UserCreatedBase):
    __tablename__ = 'comments'
    
    # Comment content
    content = db.Column(db.Text, nullable=False)
    
    # Relationships
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    
    # Comment properties
    is_human_made = db.Column(db.Boolean, default=False)  # True for manually inserted comments, False for machine-generated
    
    # Visibility and state management
    user_viewable = db.Column(db.String(20), nullable=True)  # None=visible, 'deleted'=soft deleted, 'edit'=previous edit version
    
    # Edit history tracking
    previous_comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    
    # Reply tracking
    replied_to_comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    
    # Relationships
    event = db.relationship('Event', backref='comments')
    previous_comment = db.relationship('Comment', remote_side='Comment.id', foreign_keys=[previous_comment_id], backref='next_comment')
    replied_to_comment = db.relationship('Comment', remote_side='Comment.id', foreign_keys=[replied_to_comment_id], backref='replies')
    
    def get_content_preview(self, max_length=100):
        """Get a preview of the comment content"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."
    
    def __repr__(self):
        preview = self.get_content_preview(50)
        return f'<Comment {self.id}: {preview}>'
    
    def get_columns():
        return super().get_columns() | {
            'id', 'content', 'event_id', 'is_human_made', 'user_viewable', 'previous_comment_id', 'replied_to_comment_id'
        }


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