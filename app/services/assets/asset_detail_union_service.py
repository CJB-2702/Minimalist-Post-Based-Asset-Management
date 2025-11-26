#!/usr/bin/env python3
"""
Asset Details Union Query Service
Presentation service for unified queries across all asset detail tables.

This service provides a unified way to query all asset detail tables together,
returning unified results with metadata about which table each record came from.

This file contains a service class that performs union queries across all asset detail tables
(PurchaseInfo, VehicleRegistration, ToyotaWarrantyReceipt) based on the common fields
inherited from AssetDetailVirtual and UserCreatedBase.

Now uses AssetDetailsStruct internally for structured access to detail records.
"""

from app import db
from app.data.assets.asset_details import PurchaseInfo, VehicleRegistration, ToyotaWarrantyReceipt
from app.data.assets.asset_detail_virtual import AssetDetailVirtual
from app.data.core.user_created_base import UserCreatedBase
from app.buisness.assets.asset_details.asset_details_struct import AssetDetailsStruct
from sqlalchemy import text, union_all
from typing import List, Dict, Any, Optional
from datetime import datetime


class AssetDetailUnionService:
    """
    Service class for performing union queries across all asset detail tables.
    
    This service provides methods to query all asset detail tables together,
    returning unified results with metadata about which table each record came from.
    """
    
    # List of all asset detail table classes
    ASSET_DETAIL_TABLES = [
        PurchaseInfo,
        VehicleRegistration, 
        ToyotaWarrantyReceipt
    ]
    
    @classmethod
    def get_all_details_for_asset(cls, asset_id: int) -> List[Dict[str, Any]]:
        """
        Get all detail records for a specific asset across all detail tables.
        
        Uses AssetDetailsStruct internally to get structured access to detail records.
        
        Args:
            asset_id: The ID of the asset to get details for
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        # Use AssetDetailsStruct to get structured access to all detail types
        struct = AssetDetailsStruct(asset_id)
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
        return sorted(results, key=lambda x: x['all_asset_detail_id'])
    
    @classmethod
    def get_all_details(cls, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all detail records across all asset detail tables.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        results = []
        
        for table_class in cls.ASSET_DETAIL_TABLES:
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
        return sorted(results, key=lambda x: x['all_asset_detail_id'])
    
    @classmethod
    def search_details(cls, search_term: str, asset_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search across all asset detail tables for records containing the search term.
        
        Uses AssetDetailsStruct when asset_id is provided for structured access.
        
        Args:
            search_term: Text to search for
            asset_id: Optional asset ID to limit search to
            
        Returns:
            List of dictionaries containing matching detail records with metadata
        """
        results = []
        search_term_lower = search_term.lower()
        
        # If asset_id is provided, use AssetDetailsStruct for structured access
        if asset_id:
            struct = AssetDetailsStruct(asset_id)
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
            # Search across all assets - need to query each table
            for table_class in cls.ASSET_DETAIL_TABLES:
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
        
        return sorted(results, key=lambda x: x['all_asset_detail_id'])
    
    @classmethod
    def get_details_by_date_range(cls, start_date: datetime, end_date: datetime, 
                                 asset_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get detail records created within a specific date range.
        
        Uses AssetDetailsStruct when asset_id is provided for structured access.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            asset_id: Optional asset ID to limit search to
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        results = []
        
        # If asset_id is provided, use AssetDetailsStruct for structured access
        if asset_id:
            struct = AssetDetailsStruct(asset_id)
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
            # Query across all assets - need to query each table
            for table_class in cls.ASSET_DETAIL_TABLES:
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
        
        return sorted(results, key=lambda x: x['all_asset_detail_id'])
    
    @classmethod
    def get_details_by_user(cls, user_id: int, asset_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get detail records created by a specific user.
        
        Uses AssetDetailsStruct when asset_id is provided for structured access.
        
        Args:
            user_id: ID of the user who created the records
            asset_id: Optional asset ID to limit search to
            
        Returns:
            List of dictionaries containing detail records with metadata
        """
        results = []
        
        # If asset_id is provided, use AssetDetailsStruct for structured access
        if asset_id:
            struct = AssetDetailsStruct(asset_id)
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
            # Query across all assets - need to query each table
            for table_class in cls.ASSET_DETAIL_TABLES:
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
        
        return sorted(results, key=lambda x: x['all_asset_detail_id'])
    
    @classmethod
    def _extract_common_fields(cls, record) -> Dict[str, Any]:
        """
        Extract common fields from an asset detail record.
        
        Args:
            record: An instance of an asset detail table
            
        Returns:
            Dictionary containing common fields
        """
        return {
            'id': record.id,
            'all_asset_detail_id': record.all_asset_detail_id,
            'asset_id': record.asset_id,
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
            record: An instance of an asset detail table
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
        Get statistics about all asset detail tables.
        
        Returns:
            Dictionary containing table statistics
        """
        stats = {}
        
        for table_class in cls.ASSET_DETAIL_TABLES:
            table_name = table_class.__tablename__
            count = table_class.query.count()
            stats[table_name] = {
                'table_class': table_class.__name__,
                'record_count': count
            }
        
        return stats



