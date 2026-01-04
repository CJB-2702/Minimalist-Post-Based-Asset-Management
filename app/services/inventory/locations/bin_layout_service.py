"""
Bin Layout Service

Handles SVG parsing and bin creation from bin layout SVGs.
"""

from typing import List, Dict, Any
from bs4 import BeautifulSoup
from app.logger import get_logger

logger = get_logger("asset_management.services.inventory.locations.bin_layout")


class BinLayoutService:
    """Service for parsing bin layout SVGs and extracting bin data"""
    
    @staticmethod
    def parse_svg_bins(svg_content: str) -> List[Dict[str, Any]]:
        """
        Parse SVG and extract bin elements from the 'bins' layer.
        
        Args:
            svg_content: SVG XML content as string
            
        Returns:
            List of dictionaries containing bin data:
            - label: Bin tag from inkscape:label
            - element_id: SVG element ID
            - element: BeautifulSoup element object
            
        Raises:
            ValueError: If no bins layer found or SVG is invalid
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
        
        # Find the layer with inkscape:label="bins"
        bins_layer = None
        for g in soup.find_all('g'):
            # Check for inkscape:label="bins" - BeautifulSoup handles namespaced attrs
            inkscape_label = g.get('inkscape:label') or g.get('{http://www.inkscape.org/namespaces/inkscape}label')
            if inkscape_label == 'bins':
                bins_layer = g
                break
            # Also check id="bins" as fallback
            if g.get('id') == 'bins':
                bins_layer = g
                break
        
        if not bins_layer:
            logger.warning("No 'bins' layer found in SVG")
            raise ValueError("No 'bins' layer found in SVG. Make sure there is a group with inkscape:label='bins'")
        
        bins = []
        # Find all direct child elements (rect, path, or groups) - not recursive
        for element in bins_layer.find_all(['rect', 'path', 'g'], recursive=False):
            # Get the inkscape:label attribute for the bin name
            bin_label = element.get('inkscape:label') or element.get('{http://www.inkscape.org/namespaces/inkscape}label')
            element_id = element.get('id')
            
            # Only include elements that have a label (bins should be labeled)
            if bin_label and element_id:
                bins.append({
                    'label': bin_label,
                    'element_id': element_id,
                    'element': element
                })
        
        if not bins:
            logger.warning("No bin elements found in 'bins' layer")
            raise ValueError("No bin elements found in 'bins' layer. Make sure elements have inkscape:label attributes")
        
        logger.info(f"Parsed {len(bins)} bins from SVG")
        return bins
    
    @staticmethod
    def validate_svg_structure(svg_content: str) -> Dict[str, Any]:
        """
        Validate SVG structure and return information about it.
        
        Args:
            svg_content: SVG XML content as string
            
        Returns:
            Dictionary with validation results:
            - valid: Boolean indicating if SVG is valid
            - has_bins_layer: Boolean
            - bin_count: Number of bins found
            - errors: List of error messages
            - warnings: List of warning messages
        """
        result = {
            'valid': True,
            'has_bins_layer': False,
            'bin_count': 0,
            'errors': [],
            'warnings': []
        }
        
        try:
            bins = BinLayoutService.parse_svg_bins(svg_content)
            result['has_bins_layer'] = True
            result['bin_count'] = len(bins)
        except ValueError as e:
            result['valid'] = False
            result['errors'].append(str(e))
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Unexpected error: {e}")
        
        return result


