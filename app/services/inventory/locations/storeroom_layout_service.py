"""
Storeroom Layout Service

Handles SVG parsing and location creation from SVG layouts.
"""

from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from app.logger import get_logger

logger = get_logger("asset_management.services.inventory.locations.storeroom_layout")


class StoreroomLayoutService:
    """Service for parsing storeroom layout SVGs and extracting location data"""
    
    @staticmethod
    def parse_svg_locations(svg_content: str) -> List[Dict[str, Any]]:
        """
        Parse SVG and extract location elements from the 'locations' layer.
        
        Args:
            svg_content: SVG XML content as string
            
        Returns:
            List of dictionaries containing location data:
            - label: Location identifier from inkscape:label
            - element_id: SVG element ID
            - element: BeautifulSoup element object
            
        Raises:
            ValueError: If no locations layer found or SVG is invalid
        """
        # Try different parsers - lxml is preferred for XML/SVG
        soup = None
        parser_error = None
        
        for parser in ['lxml', 'xml', 'html.parser']:
            try:
                soup = BeautifulSoup(svg_content, parser)
                break
            except Exception as e:
                parser_error = e
                logger.debug(f"Parser '{parser}' failed: {e}")
                continue
        
        if soup is None:
            error_msg = f"Failed to parse SVG XML. Parser error: {parser_error}"
            if 'xml' in str(parser_error) or 'lxml' in str(parser_error):
                error_msg += " Please install lxml: pip install lxml"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Find the layer with inkscape:label="locations"
        locations_layer = None
        for g in soup.find_all('g'):
            # Check for inkscape:label="locations" - BeautifulSoup handles namespaced attrs
            inkscape_label = g.get('inkscape:label') or g.get('{http://www.inkscape.org/namespaces/inkscape}label')
            if inkscape_label == 'locations':
                locations_layer = g
                break
            # Also check id="locations" as fallback
            if g.get('id') == 'locations':
                locations_layer = g
                break
        
        if not locations_layer:
            logger.warning("No 'locations' layer found in SVG")
            raise ValueError("No 'locations' layer found in SVG. Make sure there is a group with inkscape:label='locations'")
        
        locations = []
        # Find all direct child elements (rect, path, or groups) - not recursive
        for element in locations_layer.find_all(['rect', 'path', 'g'], recursive=False):
            # Get the inkscape:label attribute for the location name
            location_label = element.get('inkscape:label') or element.get('{http://www.inkscape.org/namespaces/inkscape}label')
            element_id = element.get('id')
            
            # Only include elements that have a label (locations should be labeled)
            if location_label and element_id:
                locations.append({
                    'label': location_label,
                    'element_id': element_id,
                    'element': element
                })
        
        if not locations:
            logger.warning("No location elements found in 'locations' layer")
            raise ValueError("No location elements found in 'locations' layer. Make sure elements have inkscape:label attributes")
        
        logger.info(f"Parsed {len(locations)} locations from SVG")
        return locations
    
    @staticmethod
    def validate_svg_structure(svg_content: str) -> Dict[str, Any]:
        """
        Validate SVG structure and return information about it.
        
        Args:
            svg_content: SVG XML content as string
            
        Returns:
            Dictionary with validation results:
            - valid: Boolean indicating if SVG is valid
            - has_locations_layer: Boolean
            - location_count: Number of locations found
            - errors: List of error messages
            - warnings: List of warning messages
        """
        result = {
            'valid': True,
            'has_locations_layer': False,
            'location_count': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            locations = StoreroomLayoutService.parse_svg_locations(svg_content)
            result['has_locations_layer'] = True
            result['location_count'] = len(locations)
        except ValueError as e:
            result['valid'] = False
            result['errors'].append(str(e))
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Unexpected error: {e}")
        
        return result
    
    @staticmethod
    def scale_svg_for_display(svg_content: str, max_height: int = 800, max_width: Optional[int] = None) -> str:
        """
        Scale SVG to fit within display constraints while maintaining aspect ratio.
        
        Scales the SVG to fit within max_height (800px) or max_width (if provided),
        whichever is more restrictive. Maintains aspect ratio.
        
        Args:
            svg_content: SVG XML content as string
            max_height: Maximum height in pixels (default: 800)
            max_width: Maximum width in pixels (optional, CSS will handle 100% width)
            
        Returns:
            Scaled SVG XML content as string with width and height attributes set
        """
        if not svg_content:
            return svg_content
        
        # Try different parsers
        soup = None
        parser_error = None
        
        for parser in ['lxml', 'xml', 'html.parser']:
            try:
                soup = BeautifulSoup(svg_content, parser)
                break
            except Exception as e:
                parser_error = e
                logger.debug(f"Parser '{parser}' failed: {e}")
                continue
        
        if soup is None:
            logger.warning(f"Failed to parse SVG for scaling: {parser_error}")
            return svg_content  # Return original if parsing fails
        
        svg_element = soup.find('svg')
        if not svg_element:
            logger.warning("No SVG element found in content")
            return svg_content
        
        # Get original dimensions
        original_width = None
        original_height = None
        
        # Try to get from viewBox (most reliable)
        viewbox = svg_element.get('viewBox')
        if viewbox:
            try:
                # viewBox format: "x y width height"
                parts = viewbox.split()
                if len(parts) >= 4:
                    original_width = float(parts[2])
                    original_height = float(parts[3])
            except (ValueError, IndexError):
                pass
        
        # Try to get from width/height attributes
        if original_width is None or original_height is None:
            width_attr = svg_element.get('width')
            height_attr = svg_element.get('height')
            
            if width_attr:
                try:
                    # Remove units if present (e.g., "100px" -> 100, "100" -> 100)
                    original_width = float(width_attr.replace('px', '').replace('pt', '').replace('mm', '').replace('cm', '').replace('in', ''))
                except (ValueError, AttributeError):
                    pass
            
            if height_attr:
                try:
                    original_height = float(height_attr.replace('px', '').replace('pt', '').replace('mm', '').replace('cm', '').replace('in', ''))
                except (ValueError, AttributeError):
                    pass
        
        # If we still don't have dimensions, return original
        if original_width is None or original_height is None or original_width <= 0 or original_height <= 0:
            logger.debug("Could not determine SVG dimensions, returning original")
            return svg_content
        
        # Calculate scale factors
        scale_for_height = max_height / original_height
        scale = scale_for_height
        
        # If max_width is provided, use the smaller scale
        if max_width is not None:
            scale_for_width = max_width / original_width
            scale = min(scale_for_height, scale_for_width)
        
        # Calculate final dimensions
        final_width = original_width * scale
        final_height = original_height * scale
        
        # Update SVG attributes
        svg_element['width'] = f"{final_width:.2f}"
        svg_element['height'] = f"{final_height:.2f}"
        
        # Ensure viewBox is set (important for proper scaling)
        if not viewbox:
            svg_element['viewBox'] = f"0 0 {original_width:.2f} {original_height:.2f}"
        
        # Add style to ensure it respects max-width: 100%
        existing_style = svg_element.get('style', '')
        style_parts = []
        if existing_style:
            style_parts.append(existing_style.rstrip(';'))
        style_parts.append('max-width: 100%')
        style_parts.append('max-height: 800px')
        svg_element['style'] = '; '.join(style_parts) + ';'
        
        # Return the modified SVG as string (soup contains the full document)
        return str(soup)


