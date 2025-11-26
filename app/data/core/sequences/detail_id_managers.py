#!/usr/bin/env python3
"""
Global ID Manager for Asset Detail Tables
Manages shared row ID generation across all asset detail tables
"""

from app.data.core.virtual_sequence_generator import VirtualSequenceGenerator

class AssetDetailIDManager(VirtualSequenceGenerator):
    """
    Manages all_asset_detail_id sequence for AssetDetailVirtual tables
    Ensures unique IDs across all asset detail tables
    """
    
    @classmethod
    def get_sequence_table_name(cls):
        """
        Return the table name for the asset detail sequence counter
        """
        return "_sequence_asset_detail_id"
    
    @classmethod
    def get_next_asset_detail_id(cls):
        """
        Get the next available asset detail ID
        Uses the base class method for thread safety
        """
        return cls.get_next_id()


class ModelDetailIDManager(VirtualSequenceGenerator):
    """
    Manages all_model_detail_id sequence for ModelDetailVirtual tables
    Ensures unique IDs across all model detail tables
    """
    
    @classmethod
    def get_sequence_table_name(cls):
        """
        Return the table name for the model detail sequence counter
        """
        return "_sequence_model_detail_id"
    
    @classmethod
    def get_next_model_detail_id(cls):
        """
        Get the next available model detail ID
        Uses the base class method for thread safety
        """
        return cls.get_next_id()



