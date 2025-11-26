"""
Asset Details Struct
Structured class that aggregates all asset detail records for a given asset.

Takes an asset_id and retrieves the top one of each detail type
(expects only one of each type per asset).
"""

from typing import Optional, Dict, Any
from app.data.assets.asset_details import (
    PurchaseInfo,
    VehicleRegistration,
    ToyotaWarrantyReceipt
)


class AssetDetailsStruct:
    """
    Structured representation of all asset detail records for an asset.
    
    Each detail type is available as a separate attribute.
    Assumes there is only one record of each detail type per asset.
    """
    
    def __init__(self, asset_id: int):
        """
        Initialize AssetDetailsStruct with an asset_id.
        
        Loads one record of each detail type for the asset.
        
        Args:
            asset_id: The ID of the asset to load details for
        """
        self.asset_id = asset_id
        
        # Load each detail type (expecting only one of each)
        self.purchase_info: Optional[PurchaseInfo] = PurchaseInfo.query.filter_by(
            asset_id=asset_id
        ).first()
        
        self.vehicle_registration: Optional[VehicleRegistration] = VehicleRegistration.query.filter_by(
            asset_id=asset_id
        ).first()
        
        self.toyota_warranty_receipt: Optional[ToyotaWarrantyReceipt] = ToyotaWarrantyReceipt.query.filter_by(
            asset_id=asset_id
        ).first()
    
    def asdict(self) -> Dict[str, Any]:
        """
        Return a dictionary mapping class names to their instances.
        
        Returns:
            Dictionary with keys as class names and values as the detail record instances (or None)
            
        Example:
            {
                'PurchaseInfo': <PurchaseInfo instance or None>,
                'VehicleRegistration': <VehicleRegistration instance or None>,
                'ToyotaWarrantyReceipt': <ToyotaWarrantyReceipt instance or None>
            }
        """
        return {
            'PurchaseInfo': self.purchase_info,
            'VehicleRegistration': self.vehicle_registration,
            'ToyotaWarrantyReceipt': self.toyota_warranty_receipt
        }
    
    def __repr__(self):
        """String representation of the asset details struct"""
        details_present = [
            name for name, value in self.asdict().items() if value is not None
        ]
        return f'<AssetDetailsStruct asset_id={self.asset_id} details={details_present}>'

