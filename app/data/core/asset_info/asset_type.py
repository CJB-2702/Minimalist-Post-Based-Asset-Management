from app.data.core.user_created_base import UserCreatedBase
from app import db

class AssetType(UserCreatedBase):
    __tablename__ = 'asset_types'
    
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    # Note: Assets now get their asset type through make_model relationship
    # No direct relationship to assets since asset_type_id was removed from Asset
    make_models = db.relationship('MakeModel', foreign_keys='MakeModel.asset_type_id')
    
    def __repr__(self):
        return f'<AssetType {self.name}>' 