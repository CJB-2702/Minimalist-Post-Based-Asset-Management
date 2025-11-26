from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from app.buisness.core.data_insertion_mixin import DataInsertionMixin

class User(UserMixin, DataInsertionMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships (no backrefs)
    created_assets = db.relationship('Asset', foreign_keys='Asset.created_by_id')
    updated_assets = db.relationship('Asset', foreign_keys='Asset.updated_by_id')
    created_locations = db.relationship('MajorLocation', foreign_keys='MajorLocation.created_by_id')
    updated_locations = db.relationship('MajorLocation', foreign_keys='MajorLocation.updated_by_id')
    created_asset_types = db.relationship('AssetType', foreign_keys='AssetType.created_by_id')
    updated_asset_types = db.relationship('AssetType', foreign_keys='AssetType.updated_by_id')
    created_make_models = db.relationship('MakeModel', foreign_keys='MakeModel.created_by_id')
    updated_make_models = db.relationship('MakeModel', foreign_keys='MakeModel.updated_by_id')
    events = db.relationship('Event', foreign_keys='Event.user_id')
    created_comments = db.relationship('Comment', foreign_keys='Comment.created_by_id')
    updated_comments = db.relationship('Comment', foreign_keys='Comment.updated_by_id')
    created_attachments = db.relationship('Attachment', foreign_keys='Attachment.created_by_id')
    updated_attachments = db.relationship('Attachment', foreign_keys='Attachment.updated_by_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_authenticated(self):
        return self.is_active
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) 