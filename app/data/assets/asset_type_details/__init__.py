#!/usr/bin/env python3
"""
Asset Details Package
"""

# Import all asset detail classes
from .purchase_info import PurchaseInfo
from .vehicle_registration import VehicleRegistration
from .toyota_warranty_receipt import ToyotaWarrantyReceipt
from .smog_record import SmogRecord

# Note: Event listeners and row ID management are now handled automatically
# by the AssetDetailVirtual base class constructor
