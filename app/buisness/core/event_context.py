"""
Event Context
Provides a clean interface for managing events, comments, and attachments.
Handles complex relational logic while using ORM models for basic operations.
"""

from typing import List, Optional, Union
from app import db
from sqlalchemy import or_, and_
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
        Get all comments for this event, ordered by creation date (oldest first for chronological display).
        Filters out deleted comments and previous edits (hidden from users).
        
        Returns:
            List of Comment objects (excluding deleted and previous edits), ordered chronologically
        """
        if self._comments is None:
            query = Comment.query.filter_by(event_id=self._event_id)
            
            # Filter out deleted comments and previous edits
            # Show only comments where user_viewable is None (visible)
            query = query.filter(
                or_(
                    Comment.user_viewable.is_(None),
                    ~Comment.user_viewable.in_(['deleted', 'edit'])
                )
            )
            
            # Order by creation date (oldest first) for chronological display
            self._comments = query.order_by(Comment.created_at.asc()).all()
        return self._comments
    
    def get_comment_edits(self, current_comment_id: int) -> List[Comment]:
        """
        Get all comment edits in the edit chain for a given comment.
        
        Queries all edit comments (user_viewable == 'edit') for this event,
        builds a dict mapping previous_comment_id to comment, then traverses
        the linked list backwards from the current comment to return all edits
        in chronological order (oldest first).
        
        Args:
            current_comment_id: ID of the current comment to get edit history for
            
        Returns:
            List of Comment objects that are edits (previous versions), ordered chronologically (oldest first)
        """
        # Query all comments associated with this event that are edits
        edit_comments = Comment.query.filter_by(
            event_id=self._event_id,
            user_viewable='edit'
        ).all()
        
        # Build a dict: parent_id (previous_comment_id) -> comment
        # This allows O(1) lookup when traversing the linked list
        # Also build reverse lookup: comment_id -> edit_comment (for finding next edit)
        edits_by_parent = {}
        edits_by_id = {}
        for edit_comment in edit_comments:
            if edit_comment.previous_comment_id:
                edits_by_parent[edit_comment.previous_comment_id] = edit_comment
            edits_by_id[edit_comment.id] = edit_comment
        
        # Traverse the linked list backwards from current_comment_id
        edit_chain = []
        visited = set()
        
        # Start from the current comment and traverse backwards
        current_comment = Comment.query.get(current_comment_id)
        if not current_comment:
            return []
        
        # Traverse backwards through the linked list
        # We want to find all edits that are part of this comment's history
        current = current_comment
        while current:
            if current.id in visited:
                break  # Prevent infinite loops
            visited.add(current.id)
            
            # If current comment is an edit, add it to the chain
            if current.user_viewable == 'edit':
                edit_chain.append(current)
            
            # Move to previous comment in chain
            if current.previous_comment_id:
                # First try the dict for O(1) lookup
                if current.previous_comment_id in edits_by_parent:
                    current = edits_by_parent[current.previous_comment_id]
            else:
                break  # Reached the original comment (no previous)
        
        # Reverse to get chronological order (oldest first)
        return list(reversed(edit_chain))
    
    def get_human_comments(self) -> List[Comment]:
        """
        Get only human-made comments for this event, ordered by creation date (newest first).
        Uses the comments property to ensure deleted and edited comments are filtered out,
        then filters further to only return human-made comments.
        
        Returns:
            List of Comment objects that are human-made (excluding deleted and previous edits)
        """
        # Use the comments property to get filtered comments (excludes deleted/edited)
        # Then filter to only human-made comments
        return [comment for comment in self.comments if comment.is_human_made]
    
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
        is_human_made: bool = False,
        replied_to_comment_id: Optional[int] = None
    ) -> Comment:
        """
        Add a comment to the event.
        
        Args:
            user_id: ID of user creating the comment (required, even for automated comments)
            content: Comment content text
            is_human_made: Whether comment was manually inserted by a human (default: False)
            replied_to_comment_id: ID of comment this is replying to (default: None)
            
        Returns:
            Created Comment instance
        """
        comment = Comment(
            content=content,
            event_id=self._event_id,
            created_by_id=user_id,
            updated_by_id=user_id,
            is_human_made=is_human_made,
            replied_to_comment_id=replied_to_comment_id,
            user_viewable=None  # Visible by default
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
        is_human_made: bool = False,
        replied_to_comment_id: Optional[int] = None,
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
            is_human_made: Whether comment was manually inserted by a human (default: False)
            replied_to_comment_id: ID of comment this is replying to (default: None)
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
        comment = self.add_comment(user_id, content, is_human_made, replied_to_comment_id)
        
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
        is_human_made: bool = False,
        replied_to_comment_id: Optional[int] = None,
        auto_commit: bool = True
    ) -> Comment:
        """
        Add an attachment to the event (creates a comment automatically).
        
        Convenience method for adding just attachments without explicit comment.
        
        Args:
            user_id: ID of user adding the attachment
            file_object: File-like object (Werkzeug FileStorage or similar)
            comment_content: Optional comment text (auto-generated if not provided)
            is_human_made: Whether comment was manually inserted by a human (default: False)
            replied_to_comment_id: ID of comment this is replying to (default: None)
            auto_commit: Whether to commit transaction automatically (default: True)
            
        Returns:
            Created Comment instance with attachment
        """
        return self.add_comment_with_attachments(
            user_id=user_id,
            content=comment_content or "",
            file_objects=[file_object],
            is_human_made=is_human_made,
            replied_to_comment_id=replied_to_comment_id,
            auto_commit=auto_commit
        )
    
    def refresh(self):
        """Refresh cached comments and attachments from database"""
        self._comments = None
        self._attachments = None
    
    def edit_comment(
        self,
        comment_id: int,
        user_id: int,
        new_content: str
    ) -> Comment:
        """
        Edit a comment by creating a new comment linked to the previous version.
        The previous comment is marked as 'edit' (hidden from users).
        
        Args:
            comment_id: ID of comment to edit
            user_id: ID of user making the edit (must be comment creator)
            new_content: New content for the comment
            
        Returns:
            New Comment instance (the edited version)
            
        Raises:
            ValueError: If comment doesn't exist or user doesn't have permission
        """
        # Get the original comment
        original_comment = Comment.query.get(comment_id)
        if not original_comment:
            raise ValueError(f"Comment {comment_id} not found")
        
        if original_comment.event_id != self._event_id:
            raise ValueError(f"Comment {comment_id} does not belong to event {self._event_id}")
        
        if original_comment.created_by_id != user_id:
            raise ValueError("You can only edit your own comments")
        
        # Mark original comment as previous edit (hidden from users)
        original_comment.user_viewable = 'edit'
        original_comment.updated_by_id = user_id
        
        # Create new comment linked to the previous one
        new_comment = self.add_comment(
            user_id=user_id,
            content=new_content,
            is_human_made=original_comment.is_human_made,
            replied_to_comment_id=original_comment.replied_to_comment_id  # Preserve reply relationship
        )
        
        # Link new comment to previous version
        new_comment.previous_comment_id = original_comment.id
        
        db.session.flush()  # Flush to get new_comment.id
        
        # Move CommentAttachment records from original comment to new comment
        comment_attachments = CommentAttachment.query.filter_by(
            attached_to_id=original_comment.id
        ).all()
        
        for comment_attachment in comment_attachments:
            comment_attachment.attached_to_id = new_comment.id
            comment_attachment.updated_by_id = user_id
            # updated_at will be automatically updated by the model's onupdate handler
        
        return new_comment
    
    def delete_comment(
        self,
        comment_id: int,
        user_id: int
    ) -> None:
        """
        Soft delete a comment by setting user_viewable to 'deleted'.
        
        Args:
            comment_id: ID of comment to delete
            user_id: ID of user deleting the comment (must be comment creator)
            
        Raises:
            ValueError: If comment doesn't exist or user doesn't have permission
        """
        comment = Comment.query.get(comment_id)
        if not comment:
            raise ValueError(f"Comment {comment_id} not found")
        
        if comment.event_id != self._event_id:
            raise ValueError(f"Comment {comment_id} does not belong to event {self._event_id}")
        
        if comment.created_by_id != user_id:
            raise ValueError("You can only delete your own comments")
        
        # Soft delete by setting user_viewable
        comment.user_viewable = 'deleted'
        comment.updated_by_id = user_id
        
        db.session.flush()
        
        # Invalidate cache
        self._comments = None
        self._attachments = None
    
    @staticmethod
    def get_comment_edit_history(comment: Union[Comment, int]) -> List[Comment]:
        """
        Get the complete edit history for a comment.
        Returns a list of all previous versions, ordered chronologically (oldest first).
        Includes the original comment and all edits in the chain.
        Includes comments marked as 'edit' (previous versions).
        
        Args:
            comment: Comment instance or comment ID
            
        Returns:
            List of Comment objects representing the edit history chain
        """
        # Get comment instance if ID provided
        if isinstance(comment, int):
            comment = Comment.query.get_or_404(comment)
        
        # Build the history chain by traversing backwards from current to original
        history_reverse = []
        visited = set()
        current = comment
        
        # Traverse backwards to find the original comment
        while current:
            if current.id in visited:
                break  # Prevent infinite loops
            visited.add(current.id)
            history_reverse.append(current)
            
            # Move to previous comment in chain
            if current.previous_comment_id:
                previous = Comment.query.get(current.previous_comment_id)
                if previous:
                    current = previous
                else:
                    break
            else:
                break  # Reached the original comment (no previous)
        
        # Reverse to get chronological order (oldest first)
        history = list(reversed(history_reverse))
        
        return history
    
    def __repr__(self):
        return f'<EventContext event_id={self._event_id} comments={len(self.comments)} attachments={len(self.attachments)}>'

