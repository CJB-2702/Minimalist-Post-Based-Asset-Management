"""
Event Context
Provides a clean interface for managing events, comments, and attachments.
Handles complex relational logic while using ORM models for basic operations.
"""

from typing import List, Optional, Union
from app import db
from app.data.core.event_info.event import Event
from app.data.core.event_info.comment import Comment, CommentAttachment
from app.data.core.event_info.attachment import Attachment


class EventContext:
    """
    Context manager for event operations including comments and attachments.
    
    Provides a clean interface for:
    - Accessing event, comments, and attachments
    - Adding comments to events
    - Adding attachments (via comments) to events
    
    Uses ORM models for basic operations but handles complex relational logic.
    """
    
    def __init__(self, event: Union[Event, int]):
        """
        Initialize EventContext with an Event instance or event ID.
        
        Args:
            event: Event instance or event ID
        """
        if isinstance(event, int):
            self._event = Event.query.get_or_404(event)
            self._event_id = event
        else:
            self._event = event
            self._event_id = event.id
        
        # Cache for lazy loading
        self._comments = None
        self._attachments = None
    
    @property
    def event(self) -> Event:
        """Get the Event instance"""
        return self._event
    
    @property
    def event_id(self) -> int:
        """Get the event ID"""
        return self._event_id
    
    @property
    def comments(self) -> List[Comment]:
        """
        Get all comments for this event, ordered by creation date (newest first).
        
        Returns:
            List of Comment objects
        """
        if self._comments is None:
            self._comments = Comment.query.filter_by(
                event_id=self._event_id
            ).order_by(Comment.created_at.desc()).all()
        return self._comments
    
    def get_human_comments(self) -> List[Comment]:
        """
        Get only human-made comments for this event, ordered by creation date (newest first).
        
        Returns:
            List of Comment objects that are human-made
        """
        return Comment.query.filter_by(
            event_id=self._event_id,
            is_human_made=True
        ).order_by(Comment.created_at.desc()).all()
    
    @property
    def attachments(self) -> List[Attachment]:
        """
        Get all attachments for this event (via comments).
        
        Returns:
            List of Attachment objects
        """
        if self._attachments is None:
            # Get all comment attachments for comments on this event
            comment_ids = [c.id for c in self.comments]
            if comment_ids:
                comment_attachments = CommentAttachment.query.filter(
                    CommentAttachment.attached_to_id.in_(comment_ids)
                ).all()
                self._attachments = [ca.attachment for ca in comment_attachments]
            else:
                self._attachments = []
        return self._attachments
    
    def add_comment(
        self,
        user_id: int,
        content: str,
        is_private: bool = False,
        is_human_made: bool = False
    ) -> Comment:
        """
        Add a comment to the event.
        
        Args:
            user_id: ID of user creating the comment
            content: Comment content text
            is_private: Whether comment is private (default: False)
            is_human_made: Whether comment was manually inserted by a human (default: False)
            
        Returns:
            Created Comment instance
        """
        comment = Comment(
            content=content,
            event_id=self._event_id,
            created_by_id=user_id,
            updated_by_id=user_id,
            is_private=is_private,
            is_human_made=is_human_made
        )
        
        db.session.add(comment)
        db.session.flush()  # Get comment ID
        
        # Invalidate cache
        self._comments = None
        self._attachments = None
        
        return comment
    
    def add_comment_with_attachments(
        self,
        user_id: int,
        content: str,
        file_objects: List,
        is_private: bool = False,
        is_human_made: bool = False,
        auto_commit: bool = True
    ) -> Comment:
        """
        Add a comment with file attachments to the event.
        
        Handles file validation, storage, and linking automatically.
        
        Args:
            user_id: ID of user creating the comment
            content: Comment content text (if empty and files provided, auto-generates)
            file_objects: List of file-like objects (Werkzeug FileStorage or similar)
                         Each should have: filename, read(), content_type attributes
            is_private: Whether comment is private (default: False)
            is_human_made: Whether comment was manually inserted by a human (default: False)
            auto_commit: Whether to commit transaction automatically (default: True)
            
        Returns:
            Created Comment instance
            
        Raises:
            ValueError: If no content and no valid files provided
        """
        # Filter out empty files
        valid_files = [
            f for f in file_objects
            if f and hasattr(f, 'filename') and f.filename
        ]
        
        # Auto-generate content if empty but files provided
        if not content.strip() and valid_files:
            content = f"Added {len(valid_files)} attachment(s)"
        
        if not content.strip() and not valid_files:
            raise ValueError("Either comment content or file attachments are required")
        
        # Create comment first
        comment = self.add_comment(user_id, content, is_private, is_human_made)
        
        # Process each file
        for file_obj in valid_files:
            try:
                # Validate file
                if not Attachment.is_allowed_file(file_obj.filename):
                    continue  # Skip invalid files (could raise exception instead)
                
                # Read file data
                file_data = file_obj.read()
                file_size = len(file_data)
                
                # Check file size
                if file_size > Attachment.MAX_FILE_SIZE:
                    continue  # Skip oversized files (could raise exception instead)
                
                # Create attachment
                attachment = Attachment(
                    filename=file_obj.filename,
                    file_size=file_size,
                    mime_type=getattr(file_obj, 'content_type', None) or 'application/octet-stream',
                    created_by_id=user_id,
                    updated_by_id=user_id,
                )
                
                # Save file to appropriate storage
                attachment.save_file(file_data, file_obj.filename)
                
                db.session.add(attachment)
                db.session.flush()  # Get attachment ID
                
                # Get current attachment count for display order
                current_attachments = CommentAttachment.query.filter_by(
                    attached_to_id=comment.id
                ).count()
                
                # Create comment attachment link
                comment_attachment = CommentAttachment(
                    attached_to_id=comment.id,
                    attachment_id=attachment.id,
                    display_order=current_attachments + 1,
                    attachment_type='Document',  # Could be determined from file type
                    created_by_id=user_id,
                    updated_by_id=user_id,
                )
                
                db.session.add(comment_attachment)
                
            except Exception as e:
                # Log error but continue with other files
                # Could raise or collect errors
                continue
        
        if auto_commit:
            db.session.commit()
        else:
            db.session.flush()
        
        # Invalidate cache
        self._comments = None
        self._attachments = None
        
        return comment
    
    def add_attachment(
        self,
        user_id: int,
        file_object,
        comment_content: Optional[str] = None,
        is_private: bool = False,
        is_human_made: bool = False,
        auto_commit: bool = True
    ) -> Comment:
        """
        Add an attachment to the event (creates a comment automatically).
        
        Convenience method for adding just attachments without explicit comment.
        
        Args:
            user_id: ID of user adding the attachment
            file_object: File-like object (Werkzeug FileStorage or similar)
            comment_content: Optional comment text (auto-generated if not provided)
            is_private: Whether comment is private (default: False)
            is_human_made: Whether comment was manually inserted by a human (default: False)
            auto_commit: Whether to commit transaction automatically (default: True)
            
        Returns:
            Created Comment instance with attachment
        """
        return self.add_comment_with_attachments(
            user_id=user_id,
            content=comment_content or "",
            file_objects=[file_object],
            is_private=is_private,
            is_human_made=is_human_made,
            auto_commit=auto_commit
        )
    
    def edit_action(
        self,
        action_id: int,
        user_id: int,
        comment_content: Optional[str] = None,
        **action_updates
    ):
        """
        Edit an action and optionally add a comment about the edit.
        
        Args:
            action_id: ID of action to edit
            user_id: ID of user making the edit
            comment_content: Optional comment content about the edit
            **action_updates: Keyword arguments to pass to ActionContext.edit_action()
            
        Returns:
            ActionContext instance after edit
        """
        from app.buisness.maintenance.base.action_context import ActionContext
        
        action_context = ActionContext(action_id)
        action_context.edit_action(**action_updates)
        
        # Add comment if provided
        if comment_content:
            self.add_comment(
                user_id=user_id,
                content=f"[Action: {action_context.action.action_name}] {comment_content}",
                is_human_made=True
            )
        
        return action_context
    
    def refresh(self):
        """Refresh cached comments and attachments from database"""
        self._comments = None
        self._attachments = None
    
    def __repr__(self):
        return f'<EventContext event_id={self._event_id} comments={len(self.comments)} attachments={len(self.attachments)}>'

