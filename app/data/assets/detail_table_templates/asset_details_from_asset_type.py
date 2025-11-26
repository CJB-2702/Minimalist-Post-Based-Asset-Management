#!/usr/bin/env python3
"""
Asset Type Detail Table Set
Configuration container that defines which detail table types are available for a specific asset type
"""

from app.data.core.user_created_base import UserCreatedBase
from app.logger import get_logger
logger = get_logger("asset_management.models.assets")
from app import db

class AssetDetailTemplateByAssetType(UserCreatedBase):
    """
    Configuration container that defines which detail table types are available for a specific asset type
    """
    __tablename__ = 'asset_details_from_asset_type'
    
    # Configuration fields
    asset_type_id = db.Column(db.Integer, db.ForeignKey('asset_types.id'), nullable=False)
    detail_table_type = db.Column(db.String(100), nullable=False)  # e.g., 'purchase_info', 'vehicle_registration'

    
    # Relationships
    asset_type = db.relationship('AssetType', backref='asset_detail_templates')
    
    def __repr__(self):
        """String representation of the asset type detail table set"""
        return f'<AssetDetailTemplateByAssetType AssetType:{self.asset_type_id}:{self.detail_table_type}>'
    
    @classmethod
    def get_detail_table_types_for_asset_type(cls, asset_type_id):
        """Get all detail table types configured for a specific asset type"""
        return cls.query.filter(
            (cls.asset_type_id == asset_type_id) | (cls.asset_type_id == None)
        ).all()