#!/usr/bin/env python3
"""
Model Details Union Query Service

WARNING: This file is for UI integration purposes only. 
DO NOT automatically integrate this into the main application unless explicitly told to do so.
This service provides a unified way to query all model detail tables together.

This file contains a service class that performs union queries across all model detail tables
(ModelInfo, EmissionsInfo) based on the common fields inherited from ModelDetailVirtual 
and UserCreatedBase.

Now uses ModelDetailsStruct internally for structured access to detail records.
"""

from app import db
from app.data.assets.model_details import ModelInfo, EmissionsInfo
from app.data.assets.model_detail_virtual import ModelDetailVirtual
from app.data.core.user_created_base import UserCreatedBase
from app.buisness.assets.model_details.model_details_struct import ModelDetailsStruct
from sqlalchemy import text, union_all
from typing import List, Dict, Any, Optional
from datetime import datetime


class ModelDetailsUnionService:
    """
    Service class for performing union queries across all model detail tables.
    
    This service provides methods to query all model detail tables together,
    returning unified results with metadata about which table each record came from.
    """
    
    # List of all model detail table classes
    # Note: When make_model_id is known, use ModelDetailsStruct for structured access
    MODEL_DETAIL_TABLES = [
        ModelInfo,
        EmissionsInfo
    ]
    
    @classmethod
    def get_all_details_for_model(cls, make_model_id: int) -> List[Dict[str, Any]]:
        """
        Get all detail records for a specific model across all detail tables.
        
        Uses ModelDetailsStruct internally to get structured access to detail records.
        
        Args:
            make_model_id: The ID of the make/model to get details for
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        # Use ModelDetailsStruct to get structured access to all detail types
        struct = ModelDetailsStruct(make_model_id)
        details_dict = struct.asdict()
        
        results = []
        
        # Convert struct to list format (for backward compatibility)
        for class_name, record in details_dict.items():
            if record is not None:
                detail_data = cls._extract_common_fields(record)
                detail_data.update({
                    'table_name': record.__tablename__,
                    'table_class': class_name,
                    'record': record
                })
                results.append(detail_data)
        
        # Sort by global ID for consistent ordering
        return sorted(results, key=lambda x: x['all_model_detail_id'])
    
    @classmethod
    def get_all_details(cls, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all detail records across all model detail tables.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        results = []
        
        for table_class in cls.MODEL_DETAIL_TABLES:
            query = table_class.query
            
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
                
            records = query.all()
            
            for record in records:
                detail_data = cls._extract_common_fields(record)
                detail_data.update({
                    'table_name': table_class.__tablename__,
                    'table_class': table_class.__name__,
                    'record': record
                })
                results.append(detail_data)
        
        # Sort by global ID for consistent ordering
        return sorted(results, key=lambda x: x['all_model_detail_id'])
    
    @classmethod
    def search_details(cls, search_term: str, make_model_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search across all model detail tables for records containing the search term.
        
        Uses ModelDetailsStruct when make_model_id is provided for structured access.
        
        Args:
            search_term: Text to search for
            make_model_id: Optional make/model ID to limit search to
            
        Returns:
            List of dictionaries containing matching detail records with metadata
        """
        results = []
        search_term_lower = search_term.lower()
        
        # If make_model_id is provided, use ModelDetailsStruct for structured access
        if make_model_id:
            struct = ModelDetailsStruct(make_model_id)
            details_dict = struct.asdict()
            
            for class_name, record in details_dict.items():
                if record is not None and cls._record_matches_search(record, search_term_lower):
                    detail_data = cls._extract_common_fields(record)
                    detail_data.update({
                        'table_name': record.__tablename__,
                        'table_class': class_name,
                        'record': record
                    })
                    results.append(detail_data)
        else:
            # Search across all models - need to query each table
            for table_class in cls.MODEL_DETAIL_TABLES:
                records = table_class.query.all()
                
                for record in records:
                    # Check if search term appears in any string field
                    if cls._record_matches_search(record, search_term_lower):
                        detail_data = cls._extract_common_fields(record)
                        detail_data.update({
                            'table_name': table_class.__tablename__,
                            'table_class': table_class.__name__,
                            'record': record
                        })
                        results.append(detail_data)
        
        return sorted(results, key=lambda x: x['all_model_detail_id'])
    
    @classmethod
    def get_details_by_date_range(cls, start_date: datetime, end_date: datetime, 
                                 make_model_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get detail records created within a specific date range.
        
        Uses ModelDetailsStruct when make_model_id is provided for structured access.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            make_model_id: Optional make/model ID to limit search to
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        results = []
        
        # If make_model_id is provided, use ModelDetailsStruct for structured access
        if make_model_id:
            struct = ModelDetailsStruct(make_model_id)
            details_dict = struct.asdict()
            
            for class_name, record in details_dict.items():
                if record is not None:
                    # Check if record falls within date range
                    if start_date <= record.created_at <= end_date:
                        detail_data = cls._extract_common_fields(record)
                        detail_data.update({
                            'table_name': record.__tablename__,
                            'table_class': class_name,
                            'record': record
                        })
                        results.append(detail_data)
        else:
            # Query across all models - need to query each table
            for table_class in cls.MODEL_DETAIL_TABLES:
                query = table_class.query.filter(
                    table_class.created_at >= start_date,
                    table_class.created_at <= end_date
                )
                
                records = query.all()
                
                for record in records:
                    detail_data = cls._extract_common_fields(record)
                    detail_data.update({
                        'table_name': table_class.__tablename__,
                        'table_class': table_class.__name__,
                        'record': record
                    })
                    results.append(detail_data)
        
        return sorted(results, key=lambda x: x['all_model_detail_id'])
    
    @classmethod
    def get_details_by_user(cls, user_id: int, make_model_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get detail records created by a specific user.
        
        Uses ModelDetailsStruct when make_model_id is provided for structured access.
        
        Args:
            user_id: ID of the user who created the records
            make_model_id: Optional make/model ID to limit search to
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        results = []
        
        # If make_model_id is provided, use ModelDetailsStruct for structured access
        if make_model_id:
            struct = ModelDetailsStruct(make_model_id)
            details_dict = struct.asdict()
            
            for class_name, record in details_dict.items():
                if record is not None and record.created_by_id == user_id:
                    detail_data = cls._extract_common_fields(record)
                    detail_data.update({
                        'table_name': record.__tablename__,
                        'table_class': class_name,
                        'record': record
                    })
                    results.append(detail_data)
        else:
            # Query across all models - need to query each table
            for table_class in cls.MODEL_DETAIL_TABLES:
                query = table_class.query.filter_by(created_by_id=user_id)
                
                records = query.all()
                
                for record in records:
                    detail_data = cls._extract_common_fields(record)
                    detail_data.update({
                        'table_name': table_class.__tablename__,
                        'table_class': table_class.__name__,
                        'record': record
                    })
                    results.append(detail_data)
        
        return sorted(results, key=lambda x: x['all_model_detail_id'])
    
    @classmethod
    def get_details_by_emissions_standard(cls, emissions_standard: str, 
                                         make_model_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get detail records by emissions standard (specific to EmissionsInfo table).
        
        Args:
            emissions_standard: Emissions standard to filter by (e.g., 'EPA', 'CARB')
            make_model_id: Optional make/model ID to limit search to
            
        Returns:
            List of dictionaries containing matching detail records with metadata
        """
        results = []
        
        # This query is specific to EmissionsInfo table
        query = EmissionsInfo.query.filter_by(emissions_standard=emissions_standard)
        
        if make_model_id:
            query = query.filter_by(make_model_id=make_model_id)
        
        records = query.all()
        
        for record in records:
            detail_data = cls._extract_common_fields(record)
            detail_data.update({
                'table_name': EmissionsInfo.__tablename__,
                'table_class': EmissionsInfo.__name__,
                'record': record
            })
            results.append(detail_data)
        
        return sorted(results, key=lambda x: x['all_model_detail_id'])
    
    @classmethod
    def get_details_by_body_style(cls, body_style: str, 
                                 make_model_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get detail records by body style (specific to ModelInfo table).
        
        Args:
            body_style: Body style to filter by (e.g., 'sedan', 'SUV', 'truck')
            make_model_id: Optional make/model ID to limit search to
            
        Returns:
            List of dictionaries containing matching detail records with metadata
        """
        results = []
        
        # This query is specific to ModelInfo table
        query = ModelInfo.query.filter_by(body_style=body_style)
        
        if make_model_id:
            query = query.filter_by(make_model_id=make_model_id)
        
        records = query.all()
        
        for record in records:
            detail_data = cls._extract_common_fields(record)
            detail_data.update({
                'table_name': ModelInfo.__tablename__,
                'table_class': ModelInfo.__name__,
                'record': record
            })
            results.append(detail_data)
        
        return sorted(results, key=lambda x: x['all_model_detail_id'])
    
    @classmethod
    def _extract_common_fields(cls, record) -> Dict[str, Any]:
        """
        Extract common fields from a model detail record.
        
        Args:
            record: An instance of a model detail table
            
        Returns:
            Dictionary containing common fields
        """
        return {
            'id': record.id,
            'all_model_detail_id': record.all_model_detail_id,
            'make_model_id': record.make_model_id,
            'created_at': record.created_at,
            'created_by_id': record.created_by_id,
            'updated_at': record.updated_at,
            'updated_by_id': record.updated_by_id
        }
    
    @classmethod
    def _record_matches_search(cls, record, search_term: str) -> bool:
        """
        Check if a record matches the search term by examining string fields.
        
        Args:
            record: An instance of a model detail table
            search_term: Lowercase search term
            
        Returns:
            True if record matches search term, False otherwise
        """
        # Get all string fields from the record
        for column in record.__table__.columns:
            if hasattr(record, column.name):
                value = getattr(record, column.name)
                if value and isinstance(value, str) and search_term in value.lower():
                    return True
        return False
    
    @classmethod
    def get_table_statistics(cls) -> Dict[str, Any]:
        """
        Get statistics about all model detail tables.
        
        Returns:
            Dictionary containing table statistics
        """
        stats = {}
        
        for table_class in cls.MODEL_DETAIL_TABLES:
            table_name = table_class.__tablename__
            count = table_class.query.count()
            stats[table_name] = {
                'table_class': table_class.__name__,
                'record_count': count
            }
        
        return stats

