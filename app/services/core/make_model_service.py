"""
Make/Model Service
Presentation service for make/model-related data retrieval and formatting.

Handles:
- Query building and filtering for make/model list views
- Count aggregation (asset counts)
- Detail view data aggregation
"""

from typing import Dict, Optional, Tuple
from flask import Request
from flask_sqlalchemy.pagination import Pagination
from app.data.core.asset_info.make_model import MakeModel
from app.data.core.asset_info.asset_type import AssetType
from app.buisness.assets.make_model_context import MakeModelDetailsContext as MakeModelContext


class MakeModelService:
    """
    Service for make/model presentation data.
    
    Provides methods for:
    - Building filtered make/model queries
    - Aggregating counts (assets) using context managers
    - Retrieving form options (asset_types)
    - Paginating make/model lists
    """
    
    @staticmethod
    def build_filtered_query(
        make: Optional[str] = None,
        asset_type_id: Optional[int] = None,
        active: Optional[bool] = None
    ):
        """
        Build a filtered make/model query.
        
        Args:
            make: Filter by make (partial match)
            asset_type_id: Filter by asset type
            active: Filter by active status
            
        Returns:
            SQLAlchemy query object
        """
        query = MakeModel.query
        
        if make:
            query = query.filter(MakeModel.make.ilike(f'%{make}%'))
        
        if asset_type_id:
            query = query.filter(MakeModel.asset_type_id == asset_type_id)
        
        if active is not None:
            query = query.filter(MakeModel.is_active == active)
        
        # Order by make, model, year
        query = query.order_by(MakeModel.make, MakeModel.model, MakeModel.year)
        
        return query
    
    @staticmethod
    def get_list_data(
        request: Request,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[Pagination, Dict, Dict]:
        """
        Get paginated make/model list with filters applied and count aggregations.
        
        Args:
            request: Flask request object
            page: Page number (default: 1)
            per_page: Items per page (default: 20)
            
        Returns:
            Tuple of (pagination object, count dict, filter options dict)
        """
        # Extract filter parameters
        make = request.args.get('make')
        asset_type_id = request.args.get('asset_type_id', type=int)
        active_param = request.args.get('active')
        active = None if active_param is None else (active_param.lower() == 'true')
        
        # Build filtered query
        query = MakeModelService.build_filtered_query(
            make=make,
            asset_type_id=asset_type_id,
            active=active
        )
        
        # Paginate
        make_models = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # Pre-calculate asset counts for each make/model using context managers
        asset_counts = {}
        for make_model in make_models.items:
            make_model_context = MakeModelContext(make_model)
            asset_counts[make_model.id] = make_model_context.asset_count
        
        # Get filter options
        filter_options = {
            'asset_types': AssetType.query.all()
        }
        
        return make_models, {'asset_counts': asset_counts}, filter_options
    
    @staticmethod
    def get_detail_data(make_model_id: int) -> Dict:
        """
        Get make/model detail data with related assets.
        
        Args:
            make_model_id: Make/Model ID
            
        Returns:
            Dictionary with make_model and assets
        """
        make_model_context = MakeModelContext(make_model_id)
        
        # Get assets of this make/model using context manager
        assets = make_model_context.get_assets()
        
        return {
            'make_model': make_model_context.model,
            'assets': assets
        }
    
    @staticmethod
    def get_form_options() -> Dict:
        """
        Get form options for make/model creation/editing.
        
        Returns:
            Dictionary with 'asset_types' key
        """
        return {
            'asset_types': AssetType.query.all()
        }

