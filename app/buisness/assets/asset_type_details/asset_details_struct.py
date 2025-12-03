"""
Asset Details Struct
Structured class that aggregates all asset detail records for a given asset.

Takes an asset_id and retrieves all records of each detail type.
Returns lists for all detail types to support many_to_one relationships.
"""

from typing import List, Dict, Any
from app.data.assets.asset_type_details import (
    PurchaseInfo,
    VehicleRegistration,
    ToyotaWarrantyReceipt,
    SmogRecord
)


class AssetDetailsStruct:
    """
    Structured representation of all asset detail records for an asset.
    
    Each detail type is available as a separate attribute.
    Returns lists for all detail types to support many_to_one relationships.
    """
    
    def __init__(self, asset_id: int):
        """
        Initialize AssetDetailsStruct with an asset_id.
        
        Loads all records of each detail type for the asset.
        
        Args:
            asset_id: The ID of the asset to load details for
        """
        self.asset_id = asset_id
        
        # Load each detail type (returns lists to support many_to_one)
        self.purchase_info: List[PurchaseInfo] = PurchaseInfo.query.filter_by(
            asset_id=asset_id
        ).all()
        
        self.vehicle_registration: List[VehicleRegistration] = VehicleRegistration.query.filter_by(
            asset_id=asset_id
        ).all()
        
        self.toyota_warranty_receipt: List[ToyotaWarrantyReceipt] = ToyotaWarrantyReceipt.query.filter_by(
            asset_id=asset_id
        ).all()
        
        self.smog_record: List[SmogRecord] = SmogRecord.query.filter_by(
            asset_id=asset_id
        ).all()
    
    def asdict(self) -> Dict[str, Any]:
        """
        Return a dictionary mapping class names to their record lists.
        
        Returns:
            Dictionary with keys as class names and values as lists of detail record instances
            
        Example:
            {
                'PurchaseInfo': [<PurchaseInfo instance>, ...],
                'VehicleRegistration': [<VehicleRegistration instance>, ...],
                'ToyotaWarrantyReceipt': [<ToyotaWarrantyReceipt instance>, ...],
                'SmogRecord': [<SmogRecord instance>, ...]
            }
        """
        return {
            'PurchaseInfo': self.purchase_info,
            'VehicleRegistration': self.vehicle_registration,
            'ToyotaWarrantyReceipt': self.toyota_warranty_receipt,
            'SmogRecord': self.smog_record
        }
    
    def __repr__(self):
        """String representation of the asset details struct"""
        details_present = [
            f"{name}({len(value)})" for name, value in self.asdict().items() if value
        ]
        return f'<AssetDetailsStruct asset_id={self.asset_id} details={details_present}>'

