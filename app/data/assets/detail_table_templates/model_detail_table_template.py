#!/usr/bin/env python3
"""
Model Detail Table Set
Configuration container that defines additional detail table types for a specific model beyond what the asset type provides
"""

from app.data.core.user_created_base import UserCreatedBase
from app.logger import get_logger
logger = get_logger("asset_management.models.assets")
from app import db

class ModelDetailTableTemplate(UserCreatedBase):
    """
    Configuration container that defines additional detail table types for a specific model beyond what the asset type provides
    """
    __tablename__ = 'model_detail_template'
    
    # Configuration fields
    asset_type_id = db.Column(db.Integer, db.ForeignKey('asset_types.id'), nullable=True)
    detail_table_type = db.Column(db.String(100), nullable=False)  # e.g., 'emissions_info', 'model_info'
    
    # Relationships
    asset_type = db.relationship('AssetType', backref='model_detail_templates')
    
    def __repr__(self):
        """String representation of the model detail table set"""
        return f'<ModelDetailTableTemplate AssetType:{self.asset_type_id}:{self.detail_table_type}>'
    
    @classmethod
    def get_detail_table_types_for_model(cls, asset_type_id):
        """Get all detail table types configured for a specific model"""
        return cls.query.filter(
            (cls.asset_type_id == asset_type_id) | (cls.asset_type_id == None)
        ).all()
    
    @classmethod
    def get_model_detail_types_for_model(cls, asset_type_id):
        """Get model detail table types configured for a specific model"""
        return cls.query.filter_by(
            asset_type_id=asset_type_id,
        ).all()