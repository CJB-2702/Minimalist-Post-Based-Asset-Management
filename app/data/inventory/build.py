"""
Phase 6: Inventory and Purchasing System Build Module

This module handles the initialization and setup of Phase 6 inventory models.
"""

from pathlib import Path
from app import db
from app.data.inventory.purchasing import (
    PurchaseOrderHeader,
    PurchaseOrderLine,
    PartDemandPurchaseOrderLink
)
from app.data.inventory.arrivals import (
    ArrivalHeader,
    ArrivalLine
)
from app.data.inventory.inventory import (
    Storeroom,
    ActiveInventory,
    InventoryMovement
)


def build_models():
    """
    Register Phase 6 inventory models with SQLAlchemy
    
    Returns:
        bool: True if successful
    """
    # Models are automatically registered when imported
    # This function ensures they're loaded
    models = [
        PurchaseOrderHeader,
        PurchaseOrderLine,
        PartDemandPurchaseOrderLink,
        ArrivalHeader,
        ArrivalLine,
        Storeroom,
        ActiveInventory,
        InventoryMovement
    ]
    
    print(f"Phase 6: Registered {len(models)} inventory models")
    return True


def create_tables():
    """
    Create database tables for Phase 6 models
    
    Returns:
        bool: True if successful
    """
    try:
        db.create_all()
        print("Phase 6: Database tables created successfully")
        return True
    except Exception as e:
        print(f"Phase 6: Error creating tables: {str(e)}")
        return False


def init_sample_data():
    """
    Create initial sample data for Phase 6 (optional)
    
    This is for development/testing purposes only
    """
    # Sample data will be created in test files
    # Not implemented here to keep production clean
    pass


def verify_relationships():
    """
    Verify that all relationships are properly configured
    
    Returns:
        bool: True if all relationships are valid
    """
    try:
        # Test PurchaseOrderHeader relationships
        assert hasattr(PurchaseOrderHeader, 'purchase_order_lines')
        assert hasattr(PurchaseOrderHeader, 'major_location')
        assert hasattr(PurchaseOrderHeader, 'event')
        
        # Test PurchaseOrderLine relationships
        assert hasattr(PurchaseOrderLine, 'purchase_order')
        assert hasattr(PurchaseOrderLine, 'part')
        assert hasattr(PurchaseOrderLine, 'part_demands')
        assert hasattr(PurchaseOrderLine, 'part_arrivals')
        
        # Test ArrivalLine relationships
        assert hasattr(ArrivalLine, 'package_header')
        assert hasattr(ArrivalLine, 'purchase_order_line')
        assert hasattr(ArrivalLine, 'part')
        assert hasattr(ArrivalLine, 'inventory_movements')
        
        # Test InventoryMovement traceability fields
        assert hasattr(InventoryMovement, 'initial_arrival_id')
        assert hasattr(InventoryMovement, 'previous_movement_id')
        assert hasattr(InventoryMovement, 'initial_arrival')
        assert hasattr(InventoryMovement, 'previous_movement')
        
        # Test Storeroom relationships
        assert hasattr(Storeroom, 'major_location')
        assert hasattr(Storeroom, 'active_inventory')
        
        # Test ActiveInventory relationships
        assert hasattr(ActiveInventory, 'part')
        assert hasattr(ActiveInventory, 'storeroom')
        assert hasattr(ActiveInventory, 'major_location_id')  # Property
        
        print("Phase 6: All relationships verified successfully")
        return True
        
    except AssertionError as e:
        print(f"Phase 6: Relationship verification failed: {str(e)}")
        return False


def get_model_info():
    """
    Get information about Phase 6 models
    
    Returns:
        dict: Model information
    """
    return {
        'phase': 6,
        'name': 'Inventory and Purchasing',
        'models': [
            {
                'name': 'PurchaseOrderHeader',
                'table': 'purchase_order_headers',
                'description': 'Purchase order documents'
            },
            {
                'name': 'PurchaseOrderLine',
                'table': 'purchase_order_lines',
                'description': 'Purchase order line items'
            },
            {
                'name': 'PartDemandPurchaseOrderLink',
                'table': 'part_demand_purchase_order_links',
                'description': 'Links part demands to PO lines'
            },
            {
                'name': 'ArrivalHeader',
                'table': 'package_headers',
                'description': 'Physical packages/shipments'
            },
            {
                'name': 'ArrivalLine',
                'table': 'part_arrivals',
                'description': 'Individual part receipts'
            },
            {
                'name': 'Storeroom',
                'table': 'storerooms',
                'description': 'Physical storerooms within major locations'
            },
            {
                'name': 'ActiveInventory',
                'table': 'active_inventory',
                'description': 'Current inventory levels by bin location'
            },
            {
                'name': 'InventoryMovement',
                'table': 'inventory_movements',
                'description': 'Inventory movement audit trail with traceability'
            }
        ],
        'features': [
            'Purchase order management',
            'Part receiving and inspection',
            'Storeroom and bin-level inventory tracking',
            '3D coordinate system for bin locations',
            'Complete traceability chain (initial_arrival_id, previous_movement_id)',
            'Integration with maintenance part demands',
            'Cost tracking and valuation',
            '6-month average cost calculation'
        ]
    }


if __name__ == '__main__':
    # Quick test
    info = get_model_info()
    print(f"\nPhase {info['phase']}: {info['name']}")
    print(f"Models: {len(info['models'])}")
    for model in info['models']:
        print(f"  - {model['name']}: {model['description']}")
    print(f"\nFeatures:")
    for feature in info['features']:
        print(f"  - {feature}")

