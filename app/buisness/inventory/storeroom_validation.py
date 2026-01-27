"""
Validation utilities for the application
"""
from flask import flash
from app.data.inventory.inventory.storeroom import Storeroom


def validate_storeroom_location_match(storeroom_id, major_location_id):
    """
    Validate that a storeroom belongs to the specified major location.
    
    Args:
        storeroom_id: ID of the storeroom to validate
        major_location_id: ID of the major location to validate against
        
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
    if not storeroom_id or not major_location_id:
        # If either is None/empty, skip validation (optional fields)
        return True, None
    
    storeroom = Storeroom.query.get(storeroom_id)
    if not storeroom:
        return False, f"Storeroom with ID {storeroom_id} not found"
    
    if storeroom.major_location_id != major_location_id:
        location_name = storeroom.major_location.name if storeroom.major_location else "Unknown"
        return False, f"Storeroom '{storeroom.room_name}' belongs to location '{location_name}', not the selected location"
    
    return True, None


def validate_storeroom_location_match_with_flash(storeroom_id, major_location_id):
    """
    Validate storeroom/location match and flash error message if invalid.
    
    Args:
        storeroom_id: ID of the storeroom to validate
        major_location_id: ID of the major location to validate against
        
    Returns:
        bool: True if valid, False if invalid
    """
    is_valid, error_message = validate_storeroom_location_match(storeroom_id, major_location_id)
    if not is_valid:
        flash(error_message, "error")
    return is_valid


