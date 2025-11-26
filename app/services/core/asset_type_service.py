"""
Asset Type Service
Presentation service for asset type-related data retrieval and formatting.

Handles:
- Query building and filtering for asset type list views
- Count aggregation (asset counts, make/model counts)
- Form option retrieval (categories)
"""

from typing import Dict, Optional, Tuple
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from app import db
from app.data.core.asset_info.asset_type import AssetType
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.asset_info.asset import Asset


class AssetTypeService:
    """
    Service for asset type presentation data.
    
    Provides methods for:
    - Building filtered asset type queries
    - Aggregating counts (assets, make/models)
    - Retrieving form options (categories)
    - Paginating asset type lists
    """
    
    @staticmethod
    def build_filtered_query(
        category: Optional[str] = None,
        active: Optional[bool] = None
    ):
        """
        Build a filtered asset type query.
        
        Args:
            category: Filter by category
            active: Filter by active status
            
        Returns:
            SQLAlchemy query object
        """
        query = AssetType.query
        
        if category:
            query = query.filter(AssetType.category == category)
        
        if active is not None:
            query = query.filter(AssetType.is_active == active)
        
        # Order by name
        query = query.order_by(AssetType.name)
        
        return query
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[Pagination, Dict, Dict]:
        """
        Get paginated asset type list with filters applied and count aggregations.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Tuple of (pagination object, count dicts, filter options dict)
        """
        # Extract filter parameters
        category = request.args.get('category')
        active_param = request.args.get('active')
        active = None if active_param is None else (active_param.lower() == 'true')
        
        # Build filtered query
        query = AssetTypeService.build_filtered_query(category=category, active=active)
        
        # Paginate
        asset_types = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Pre-calculate asset counts for each asset type to avoid N+1 queries
        asset_type_counts = {}
        make_model_counts = {}
        
        for asset_type in asset_types.items:
            # Count make/models for this asset type
            make_model_count = MakeModel.query.filter_by(asset_type_id=asset_type.id).count()
            make_model_counts[asset_type.id] = make_model_count
            
            # Count assets for this asset type (through make/models)
            asset_count = db.session.query(Asset).join(MakeModel).filter(
                MakeModel.asset_type_id == asset_type.id
            ).count()
            asset_type_counts[asset_type.id] = asset_count
        
        # Get unique categories for filter
        categories = db.session.query(AssetType.category).distinct().all()
        categories = [cat[0] for cat in categories if cat[0]]
        
        count_dicts = {
            'asset_type_counts': asset_type_counts,
            'make_model_counts': make_model_counts
        }
        
        filter_options = {
            'categories': categories
        }
        
        return asset_types, count_dicts, filter_options
    
    @staticmethod
    def get_detail_data(asset_type_id: int) -> Dict:
        """
        Get asset type detail data with related make/models and assets.
        
        Args:
            asset_type_id: Asset type ID
            
        Returns:
            Dictionary with asset_type, make_models, and assets
        """
        asset_type = AssetType.query.get_or_404(asset_type_id)
        
        # Get make/models of this type
        make_models = MakeModel.query.filter_by(
            asset_type_id=asset_type_id
        ).order_by(MakeModel.make, MakeModel.model).all()
        
        # Get assets of this type (through make/models)
        assets = []
        for make_model in make_models:
            assets.extend(make_model.assets)
        
        return {
            'asset_type': asset_type,
            'make_models': make_models,
            'assets': assets
        }

