#!/usr/bin/env python3
"""
Asset Type Detail Table Set
Configuration container that defines which detail table types are available for a specific asset type
"""

from app.data.core.user_created_base import UserCreatedBase
from app.logger import get_logger
logger = get_logger("asset_management.models.assets")
from app import db

class AssetDetailTemplateByModelType(UserCreatedBase):
    """
    Configuration container that defines which detail table types are available for a specific asset type
    """
    __tablename__ = 'asset_details_from_model_type'
    
    make_model_id = db.Column(db.Integer, db.ForeignKey('make_models.id'), nullable=True)
    detail_table_type = db.Column(db.String(100), nullable=False)  # e.g., 'toyota_warranty_receipt'
    many_to_one = db.Column(db.Boolean, default=False)

    # Relationships
    make_model = db.relationship('MakeModel', backref='model_type_detail_templates')
    
    def __repr__(self):
        """String representation of the model type detail table set"""
        return f'<AssetDetailTemplateByModelType Model:{self.make_model_id}:{self.detail_table_type}>'
    
    @classmethod
    def get_detail_table_types_for_model_type(cls, make_model_id):
        """Get all detail table types configured for a specific asset type"""
        return cls.query.filter(
            cls.make_model_id == make_model_id
        ).all()