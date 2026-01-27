"""
Storeroom Visual Tools Service

Shared utilities for storeroom visualization across different portals:
- move_inventory_gui
- storeroom/view
- storeroom/build

Provides common functions for:
- Loading storeroom location data
- Scaling SVG content for display
- Preparing bin lists for templates
"""
from typing import List, Dict, Optional, Tuple
from app.buisness.inventory.locations.storeroom_context import StoreroomContext
from app.services.inventory.locations.storeroom_layout_service import StoreroomLayoutService
from app.data.inventory.inventory.storeroom import Storeroom
from app.data.inventory.locations.location import Location
from app.data.inventory.locations.bin import Bin
from app.logger import get_logger

logger = get_logger("asset_management.services.inventory.storeroom_visual_tools")


class StoreroomVisualTools:
    """Shared utilities for storeroom visualization portals"""
    
    @staticmethod
    def load_storeroom_locations(storeroom_id: int, load_bins: bool = True) -> List[Location]:
        """
        Load all locations for a storeroom with optional bin loading.
        
        Args:
            storeroom_id: ID of the storeroom
            load_bins: If True, trigger lazy load of bins for each location
            
        Returns:
            List of Location objects
        """
        storeroom_context = StoreroomContext(storeroom_id)
        location_contexts = storeroom_context.locations
        locations = [loc_ctx.location for loc_ctx in location_contexts]
        
        if load_bins:
            # Trigger lazy load of bins for each location
            for location in locations:
                if location.bins:
                    _ = location.bins  # Trigger lazy load
        
        return locations
    
    @staticmethod
    def scale_svg_for_display(svg_content: Optional[str], 
                             max_height: int = 800,
                             max_width: Optional[int] = None,
                             fallback_on_error: bool = True) -> Optional[str]:
        """
        Scale SVG content for display in viewer portals.
        
        Args:
            svg_content: Original SVG content string
            max_height: Maximum height for scaled SVG
            max_width: Optional maximum width for scaled SVG
            fallback_on_error: If True, return original SVG on error; otherwise return None
            
        Returns:
            Scaled SVG content string, or None/original on error
        """
        if not svg_content:
            return None
        
        try:
            scaled_svg = StoreroomLayoutService.scale_svg_for_display(
                svg_content,
                max_height=max_height,
                max_width=max_width
            )
            return scaled_svg
        except Exception as e:
            logger.warning(f"Failed to scale SVG for display: {e}")
            if fallback_on_error:
                return svg_content
            return None
    
    @staticmethod
    def get_selected_location(location_id: Optional[int],
                             storeroom_id: Optional[int] = None) -> Optional[Location]:
        """
        Get selected location by ID, optionally validating it belongs to storeroom.
        
        Args:
            location_id: ID of the location to retrieve
            storeroom_id: Optional storeroom ID to validate location belongs to
            
        Returns:
            Location object if found (and valid), None otherwise
        """
        if not location_id:
            return None
        
        selected_location = Location.query.get(location_id)
        
        if selected_location and storeroom_id:
            # Validate location belongs to storeroom
            if selected_location.storeroom_id != storeroom_id:
                logger.warning(f"Location {location_id} does not belong to storeroom {storeroom_id}")
                return None
        
        return selected_location
    
    @staticmethod
    def prepare_bins_list(location: Optional[Location], 
                         include_display_name: bool = True) -> List[Dict[str, any]]:
        """
        Prepare bins list in dict format for template rendering.
        
        Args:
            location: Location object with bins relationship
            include_display_name: If True, include display_name field (defaults to bin_tag)
            
        Returns:
            List of dicts with bin data: [{'id': int, 'bin_tag': str, 'display_name': str}]
        """
        if not location or not location.bins:
            return []
        
        bins_list = []
        for bin_obj in location.bins:
            bin_dict = {
                'id': bin_obj.id,
                'bin_tag': bin_obj.bin_tag,
            }
            if include_display_name:
                # Use display_name if available, otherwise use bin_tag
                bin_dict['display_name'] = getattr(bin_obj, 'display_name', None) or bin_obj.bin_tag
            bins_list.append(bin_dict)
        
        return bins_list
    
    @staticmethod
    def prepare_location_viewer_data(storeroom_id: Optional[int],
                                    max_svg_height: int = 800) -> Tuple[Optional[Storeroom], 
                                                                        List[Location], 
                                                                        Optional[str]]:
        """
        Prepare location viewer data for template rendering.
        
        Loads storeroom, locations, and scaled SVG content.
        
        Args:
            storeroom_id: ID of the storeroom to load
            max_svg_height: Maximum height for SVG scaling
            
        Returns:
            Tuple of (selected_storeroom, locations, scaled_svg_content)
        """
        selected_storeroom = None
        locations = []
        scaled_svg_content = None
        
        if storeroom_id:
            selected_storeroom = Storeroom.query.get(storeroom_id)
            if selected_storeroom:
                locations = StoreroomVisualTools.load_storeroom_locations(
                    storeroom_id,
                    load_bins=True
                )
                
                # Scale SVG for display
                scaled_svg_content = StoreroomVisualTools.scale_svg_for_display(
                    selected_storeroom.svg_content,
                    max_height=max_svg_height
                )
        
        return selected_storeroom, locations, scaled_svg_content
    
    @staticmethod
    def prepare_bin_viewer_data(location_id: Optional[int],
                               storeroom_id: Optional[int] = None) -> Tuple[Optional[Location],
                                                                           List[Dict[str, any]]]:
        """
        Prepare bin viewer data for template rendering.
        
        Args:
            location_id: ID of the location to load bins for
            storeroom_id: Optional storeroom ID to validate location
            
        Returns:
            Tuple of (selected_location, bins_list)
        """
        selected_location = StoreroomVisualTools.get_selected_location(
            location_id,
            storeroom_id
        )
        
        bins_list = StoreroomVisualTools.prepare_bins_list(selected_location)
        
        return selected_location, bins_list

