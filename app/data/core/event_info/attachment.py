from app.data.core.user_created_base import UserCreatedBase
from app import db
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from pathlib import Path
# AttachmentIDManager moved to app.models.core.sequences

class Attachment(UserCreatedBase):
    __tablename__ = 'attachments'
    
    # File information
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    mime_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    tags = db.Column(db.JSON, nullable=True)  # For categorization
    
    # Storage information
    storage_type = db.Column(db.String(20), nullable=False, default='database')  # 'database' or 'filesystem'
    file_path = db.Column(db.String(500), nullable=True)  # Path for filesystem storage
    file_data = db.Column(db.LargeBinary, nullable=True)  # BLOB for database storage
    
    # Constants
    STORAGE_THRESHOLD = 1024 * 1024  # 1MB threshold
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB max file size
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        'images': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'},
        'documents': {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',  '.rtf'},
        'archives': {'.zip', '.rar', '.7z', '.tar', '.gz'},
        'data': {'.csv', '.json', '.xml', '.sql',  'html', '.txt' ,'.log', '.data'},
        'code': {'.cpp','.py','.java','.js','.html','.css','.php','.sql','.json','.xml','.csv','.txt','.log','.data'}
    }
    #  implement later. don't forget.
    # 'audio': {'.mp3','mp4','.wav','.ogg'},
    # 'video': {'.mp4','.avi','.mov','.wmv','.flv','.mpeg','.mpg','.m4v','.webm','.mkv'},
    def get_metadata_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'filename': self.filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'description': self.description,
            'tags': self.tags,
            'storage_type': self.storage_type,
            'file_path': self.file_path,
            'created_at': self.created_at,
            'created_by_id': self.created_by_id,
            'created_by_username': self.created_by.username if self.created_by else None,
            'updated_at': self.updated_at,
            'updated_by_id': self.updated_by_id,
            'updated_by_username': self.updated_by.username if self.updated_by else None,
        }

    @classmethod
    def get_allowed_extensions(cls):
        """Get all allowed file extensions"""
        all_extensions = set()
        for category in cls.ALLOWED_EXTENSIONS.values():
            all_extensions.update(category)
        return all_extensions
    
    @classmethod
    def is_allowed_file(cls, filename):
        """Check if file extension is allowed"""
        if not filename:
            return False
        
        file_ext = Path(filename).suffix.lower()
        return file_ext in cls.get_allowed_extensions()
    
    @classmethod
    def determine_storage_type(cls, file_size):
        """Determine storage type based on file size"""
        return 'database' if file_size <= cls.STORAGE_THRESHOLD else 'filesystem'
    
    @classmethod
    def generate_file_path(cls, row_id, filename):
        """Generate filesystem path for large attachments using row_id_filename structure"""
        timestamp = datetime.now()
        safe_filename = secure_filename(filename)
        return f"instance/large_attachments/{timestamp.year}/{timestamp.month:02d}/{row_id}_{safe_filename}"
    
    def save_file(self, file_data, filename):
        """Save file data to appropriate storage"""
        self.filename = filename
        self.file_size = len(file_data)
        self.storage_type = self.determine_storage_type(self.file_size)
        
        if self.storage_type == 'database':
            self.file_data = file_data
            self.file_path = None
        else:
            # Save to filesystem
            self.file_path = self.generate_file_path(self.id, filename)
            self.file_data = None
            
            # Ensure directory exists
            file_dir = Path(self.file_path).parent
            file_dir.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(self.file_path, 'wb') as f:
                f.write(file_data)
    
    def get_file_data(self):
        """Get file data from appropriate storage"""
        if self.storage_type == 'database':
            return self.file_data
        else:
            # Read from filesystem
            if self.file_path and os.path.exists(self.file_path):
                with open(self.file_path, 'rb') as f:
                    return f.read()
            return None
    
    def delete_file(self):
        """Delete file from storage"""
        if self.storage_type == 'filesystem' and self.file_path:
            try:
                if os.path.exists(self.file_path):
                    os.remove(self.file_path)
                    
                    # Try to remove empty directories
                    file_dir = Path(self.file_path).parent
                    if file_dir.exists() and not any(file_dir.iterdir()):
                        file_dir.rmdir()
                        
                        # Try to remove parent month directory if empty
                        month_dir = file_dir.parent
                        if month_dir.exists() and not any(month_dir.iterdir()):
                            month_dir.rmdir()
                            
                            # Try to remove parent year directory if empty
                            year_dir = month_dir.parent
                            if year_dir.exists() and not any(year_dir.iterdir()):
                                year_dir.rmdir()
            except OSError:
                pass  # File might already be deleted
    
    def get_file_url(self):
        """Get URL for file download"""
        return f"/attachments/{self.id}/download"
    
    def get_file_extension(self):
        """Get file extension"""
        return Path(self.filename).suffix.lower()
    
    def is_image(self):
        """Check if file is an image"""
        return self.get_file_extension() in self.ALLOWED_EXTENSIONS['images']
    
    def is_document(self):
        """Check if file is a document"""
        return self.get_file_extension() in self.ALLOWED_EXTENSIONS['documents']
    
    def is_viewable_as_text(self):
        """Check if file can be viewed as text in browser"""
        text_extensions = self.ALLOWED_EXTENSIONS['data'] | self.ALLOWED_EXTENSIONS['code']
        return self.get_file_extension() in text_extensions
    
    def get_file_icon(self):
        """Get appropriate Bootstrap icon for file type"""
        ext = self.get_file_extension()
        
        if self.is_image():
            return 'bi-image'
        elif ext in {'.pdf'}:
            return 'bi-file-earmark-pdf'
        elif ext in {'.doc', '.docx'}:
            return 'bi-file-earmark-word'
        elif ext in {'.xls', '.xlsx'}:
            return 'bi-file-earmark-excel'
        elif ext in {'.ppt', '.pptx'}:
            return 'bi-file-earmark-ppt'
        elif ext in {'.zip', '.rar', '.7z', '.tar', '.gz'}:
            return 'bi-file-earmark-zip'
        elif ext in {'.py'}:
            return 'bi-filetype-py'
        elif ext in {'.js'}:
            return 'bi-filetype-js'
        elif ext in {'.html', '.htm'}:
            return 'bi-filetype-html'
        elif ext in {'.css'}:
            return 'bi-filetype-css'
        elif ext in {'.json'}:
            return 'bi-filetype-json'
        elif ext in {'.xml'}:
            return 'bi-filetype-xml'
        elif ext in {'.csv'}:
            return 'bi-filetype-csv'
        elif ext in {'.sql'}:
            return 'bi-filetype-sql'
        elif ext in {'.txt', '.log', '.data'}:
            return 'bi-file-earmark-text'
        else:
            return 'bi-file-earmark'
    
    def get_file_size_display(self):
        """Get human-readable file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024.0:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024.0
        return f"{self.file_size:.1f} TB"
    
    def __repr__(self):
        return f'<Attachment {self.filename} ({self.get_file_size_display()})>' 


class VirtualAttachmentReference(UserCreatedBase):
    __abstract__ = True

    # Relationships
    attachment_id = db.Column(db.Integer, db.ForeignKey('attachments.id'), nullable=False)
    all_attachment_references_id = db.Column(db.Integer, nullable=False) 
    #attached_to_id = db.Column(db.Integer, nullable=False) # this is defined in each child class with proper foreign key
    attached_to_type = db.Column(db.String(20), nullable=False)
    display_order = db.Column(db.Integer, nullable=False)
    
    # Note: attached_to_id is defined in each child class with proper foreign key
    
    # Core fields
    attachment_type = db.Column(db.String(20), nullable=False)  # 'Image', 'Document', 'Video'
    caption = db.Column(db.String(255), nullable=True)  # Optional caption for the attachment
    
    def __init__(self, *args, **kwargs):
        """Initialize the attachment reference record with global ID assignment"""
        # Assign global ID before calling parent constructor
        if 'all_attachment_references_id' not in kwargs:
            from app.data.core.sequences import AttachmentIDManager
            kwargs['all_attachment_references_id'] = AttachmentIDManager.get_next_attachment_id()
        super().__init__(*args, **kwargs) 
    
    def get_attachment(self):
        """Get attachment"""
        return Attachment.query.get(self.attachment_id)
    
    @classmethod
    def get_column_dict(cls) -> set:
        """Get set of column names for this model (excluding audit fields and relationship-only fields)."""
        return {
            'attachment_id', 'all_attachment_references_id', 'attached_to_type', 
            'display_order', 'attachment_type', 'caption'
        }