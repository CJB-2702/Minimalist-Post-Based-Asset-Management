"""
Storeroom Factory

Creates storerooms and locations with business logic.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import re
from app import db
from app.data.inventory.inventory.storeroom import Storeroom
from app.data.inventory.locations.location import Location
from app.buisness.inventory.locations.storeroom_context import StoreroomContext
from app.buisness.inventory.locations.location_context import LocationContext
from app.logger import get_logger

logger = get_logger("asset_management.buisness.inventory.locations.factory")

# Register namespaces to preserve them in output
ET.register_namespace('', 'http://www.w3.org/2000/svg')
ET.register_namespace('inkscape', 'http://www.inkscape.org/namespaces/inkscape')
ET.register_namespace('sodipodi', 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd')
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

# Namespace URIs
SVG_NS = 'http://www.w3.org/2000/svg'
INKSCAPE_NS = 'http://www.inkscape.org/namespaces/inkscape'

# Configuration for location vs bin processing
LAYER_CONFIG = {
    "location": {
        "layer_name": "locations",
        "id_prefix": "location-",
        "onclick_function": "locationSelected"
    },
    "bin": {
        "layer_name": "bins",
        "id_prefix": "bin-",
        "onclick_function": "binSelected"
    }
}


@dataclass
class BinContextWrapper:
    """Wrapper for bin data to match LocationContext interface for postprocessing."""
    location: Any  # Has .location attribute (the cleaned label)
    location_id: int  # The bin ID (named location_id for compatibility with postprocess)


class StoreroomFactory:
    """
    Factory for creating storerooms and locations.
    
    Handles creation logic and validation.
    """
    
    @staticmethod
    def _get_namespaces() -> Dict[str, str]:
        """Get namespace dictionary for XPath queries."""
        return {
            'svg': SVG_NS,
            'inkscape': INKSCAPE_NS,
            'sodipodi': 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
            'xlink': 'http://www.w3.org/1999/xlink'
        }
    
    @staticmethod
    def _clean_label(label: str) -> str:
        """
        Clean label for database storage: replace spaces with dashes, remove apostrophes.
        
        Args:
            label: Original label from SVG
            
        Returns:
            Cleaned label suitable for database storage
        """
        return label.replace(' ', '-').replace("'", '')
    
    @staticmethod
    def _format_svg_for_display(root: ET.Element, id_prefix: str) -> None:
        """
        Format SVG root element for responsive display.
        
        Sets viewBox, width, preserveAspectRatio, and styling attributes.
        
        Args:
            root: SVG root element
            id_prefix: Prefix for CSS class (e.g., "location-" or "bin-")
        """
        width_str = root.get('width') or '0'
        height_str = root.get('height') or '0'
        width_attr = int(float(re.sub(r'[^\d.]', '', width_str)))
        height_attr = int(float(re.sub(r'[^\d.]', '', height_str)))
        
        root.set('class', f"{id_prefix}svg-container")
        root.set('viewBox', f'0 0 {width_attr} {height_attr}')
        root.set('style', 'max-height: 500px;')
        root.set('preserveAspectRatio', 'xMidYMid meet')
        root.set('width', "100%")
        # Height is omitted to allow aspect ratio preservation via viewBox
    
    @staticmethod
    def _find_layer_group(root: ET.Element, layer_name: str) -> Optional[ET.Element]:
        """
        Find the layer group by inkscape:label or id.
        
        Args:
            root: SVG root element
            layer_name: Name of the layer to find (e.g., "locations" or "bins")
            
        Returns:
            Layer group element or None if not found
        """
        ns = StoreroomFactory._get_namespaces()
        label_key = f"{{{INKSCAPE_NS}}}label"
        
        # Try to find by inkscape:label using XPath
        xpath_query = f".//svg:g[@inkscape:label='{layer_name}']"
        layer_groups = root.findall(xpath_query, ns)
        
        if layer_groups:
            return layer_groups[0]
        
        # Fallback: find by id
        xpath_fallback = f".//svg:g[@id='{layer_name}']"
        layer_groups = root.findall(xpath_fallback, ns)
        
        if layer_groups:
            return layer_groups[0]
        
        # Fallback: iterate through all groups
        for g in root.iter('g'):
            if g.get(label_key) == layer_name or g.get('id') == layer_name:
                return g
        
        return None
    
    @staticmethod
    def _get_layer_elements(layer: ET.Element, layer_name: str) -> List[ET.Element]:
        """
        Get all immediate child elements from a layer group.
        
        Args:
            layer: Layer group element
            layer_name: Name of the layer (for XPath fallback)
            
        Returns:
            List of child elements
        """
        ns = StoreroomFactory._get_namespaces()
        xpath_query = f".//svg:g[@inkscape:label='{layer_name}']/*"
        elements = layer.findall(xpath_query, ns)
        
        # If XPath didn't work, fall back to direct children
        if not elements:
            elements = list(layer)
        
        return elements
    
    @staticmethod
    def preprocess_svg(svg_xml: str, location_or_bin: str = "location") -> Tuple[str, List[str]]:
        """
        Preprocess SVG: format for display, clean and update labels, validate uniqueness.
        
        Processing steps:
        1. Parse SVG XML
        2. Format SVG for responsive display (viewBox, width, etc.)
        3. Find locations or bins layer
        4. Clean labels (spaces->dashes, remove apostrophes) and update in SVG
        5. Validate all labels are unique
        6. Return processed SVG and list of cleaned labels
        
        Args:
            svg_xml: Raw SVG XML content
            location_or_bin: Either "location" or "bin" to determine which layer to process
            
        Returns:
            Tuple of (processed_svg_xml, list_of_cleaned_labels)
            
        Raises:
            ValueError: If validation fails (duplicates, no layer found, etc.)
        """
        if location_or_bin not in ("location", "bin"):
            raise ValueError(f"location_or_bin must be 'location' or 'bin', got '{location_or_bin}'")
        
        config = LAYER_CONFIG[location_or_bin]
        layer_name = config["layer_name"]
        id_prefix = config["id_prefix"]
        
        try:
            root = ET.fromstring(svg_xml)
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse SVG XML: {e}")
        
        # Format SVG for responsive display
        StoreroomFactory._format_svg_for_display(root, id_prefix)
        
        # Find the layer group
        layer = StoreroomFactory._find_layer_group(root, layer_name)
        if not layer:
            raise ValueError(f"No '{layer_name}' layer found in SVG. Make sure there is a group with inkscape:label='{layer_name}'")
        
        # Get all elements in the layer
        elements = StoreroomFactory._get_layer_elements(layer, layer_name)
        
        # Clean labels, update in SVG, and validate uniqueness
        labels = []
        seen_labels = set()
        label_key = f"{{{INKSCAPE_NS}}}label"
        
        for element in elements:
            original_label = element.get(label_key)
            
            if not original_label:
                continue
            
            # Clean the label
            cleaned_label = StoreroomFactory._clean_label(original_label)
            
            # Check for duplicates
            if cleaned_label in seen_labels:
                raise ValueError(
                    f"Duplicate {location_or_bin} label found: '{cleaned_label}' "
                    f"(original: '{original_label}'). Each {location_or_bin} must have a unique label."
                )
            
            seen_labels.add(cleaned_label)
            labels.append(cleaned_label)
            
            # Update the label in the SVG to the cleaned version
            element.set(label_key, cleaned_label)
        
        if not labels:
            raise ValueError(f"No {location_or_bin} elements with labels found in '{layer_name}' layer")
        
        # Convert tree back to string
        processed_svg = ET.tostring(root, encoding='unicode', method='xml')
        
        logger.info(f"Preprocessed SVG: {len(labels)} {location_or_bin}s found and validated")
        
        return processed_svg, labels
    
    @staticmethod
    def postprocess_svg(svg_xml: str, location_contexts: List[LocationContext], 
                       location_or_bin: str = "location") -> str:
        """
        Postprocess SVG: update element IDs, onclick handlers, and data attributes.
        
        Matches SVG labels (which are cleaned) to database records and updates:
        - Element IDs to prefixed database IDs (e.g., "location-123" or "bin-456")
        - onclick handlers with database IDs
        - data-location-id and data-location-name attributes
        
        Args:
            svg_xml: Processed SVG XML content (from preprocess_svg)
            location_contexts: List of LocationContext objects for created locations/bins
            location_or_bin: Either "location" or "bin" to determine which layer to process
            
        Returns:
            Postprocessed SVG XML content with updated element IDs and handlers
            
        Raises:
            ValueError: If SVG parsing fails
        """
        if location_or_bin not in ("location", "bin"):
            raise ValueError(f"location_or_bin must be 'location' or 'bin', got '{location_or_bin}'")
        
        config = LAYER_CONFIG[location_or_bin]
        layer_name = config["layer_name"]
        id_prefix = config["id_prefix"]
        onclick_function = config["onclick_function"]
        
        try:
            root = ET.fromstring(svg_xml)
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse SVG XML: {e}")
        
        # Find the layer
        layer = StoreroomFactory._find_layer_group(root, layer_name)
        if not layer:
            logger.warning(f"No '{layer_name}' layer found in SVG for postprocessing")
            return svg_xml
        
        # Create mapping of cleaned labels to database IDs
        # The location.location field contains the cleaned label
        # For locations: location_id is the location ID
        # For bins: location_id is the bin ID (via BinContextWrapper)
        label_to_id = {}
        for loc_ctx in location_contexts:
            cleaned_label = loc_ctx.location.location
            db_id = loc_ctx.location_id
            label_to_id[cleaned_label] = db_id
        
        # Update element IDs and attributes
        label_key = f"{{{INKSCAPE_NS}}}label"
        updated_count = 0
        
        for element in layer:
            cleaned_label = element.get(label_key)
            
            if cleaned_label and cleaned_label in label_to_id:
                db_id = label_to_id[cleaned_label]
                prefixed_id = f"{id_prefix}{db_id}"
                
                element.set('id', prefixed_id)
                element.set('onclick', f"{onclick_function}({db_id})")
                element.set(f'data-{location_or_bin}-id', str(db_id))
                element.set(f'data-{location_or_bin}-name', cleaned_label)
                updated_count += 1
        
        # Convert tree back to string
        postprocessed_svg = ET.tostring(root, encoding='unicode', method='xml')
        
        logger.info(f"Postprocessed SVG: updated {updated_count} {location_or_bin} element IDs to database IDs")
        
        return postprocessed_svg
    
    @staticmethod
    def create_storeroom(form_fields: Dict[str, Any], user_id: Optional[int] = None) -> StoreroomContext:
        """
        Create a new storeroom from form fields.
        
        Args:
            form_fields: Dictionary containing:
                - room_name: Storeroom name (required)
                - major_location_id: Major location ID (required)
                - address: Optional address/notes
            user_id: ID of user creating the storeroom
            
        Returns:
            StoreroomContext for the created storeroom
            
        Raises:
            ValueError: If required fields are missing or validation fails
        """
        room_name = form_fields.get('room_name', '').strip()
        major_location_id = form_fields.get('major_location_id')
        address = form_fields.get('address', '').strip()
        
        if not room_name:
            raise ValueError("Storeroom name is required")
        
        if not major_location_id:
            raise ValueError("Major location is required")
        
        # Validate major location exists
        from app.data.core.major_location import MajorLocation
        major_location = MajorLocation.query.get(major_location_id)
        if not major_location:
            raise ValueError(f"Major location with ID {major_location_id} not found")
        
        # Create storeroom
        storeroom = Storeroom(
            room_name=room_name,
            major_location_id=major_location_id,
            address=address,
            created_by_id=user_id,
            updated_by_id=user_id
        )
        
        db.session.add(storeroom)
        db.session.flush()
        
        logger.info(f"Created storeroom: {room_name} (ID: {storeroom.id})")
        
        return StoreroomContext(storeroom.id)
    
    @staticmethod
    def create_storeroom_from_svg(form_fields: Dict[str, Any], svg_xml: str, 
                                 user_id: Optional[int] = None) -> StoreroomContext:
        """
        Create a new storeroom from form fields and SVG layout.
        
        Flow:
        1. Preprocess SVG (format, clean labels, validate)
        2. Create storeroom
        3. Create locations from cleaned labels
        4. Postprocess SVG (update IDs, onclick, data attributes)
        
        Args:
            form_fields: Dictionary containing storeroom form fields
            svg_xml: SVG XML content for storeroom layout (raw/unprocessed)
            user_id: ID of user creating the storeroom
            
        Returns:
            StoreroomContext for the created storeroom
            
        Raises:
            ValueError: If required fields are missing or SVG parsing/validation fails
        """
        # Preprocess SVG: format, clean labels, validate uniqueness
        try:
            processed_svg, location_labels = StoreroomFactory.preprocess_svg(svg_xml, location_or_bin="location")
        except ValueError as e:
            raise ValueError(f"SVG preprocessing failed: {e}")
        
        # Create storeroom
        storeroom_context = StoreroomFactory.create_storeroom(form_fields, user_id)
        
        # Store both raw and processed SVG content
        storeroom_context.storeroom.raw_svg = svg_xml
        storeroom_context.storeroom.svg_content = processed_svg
        db.session.flush()
        
        # Create locations from cleaned labels
        location_contexts = []
        for label in location_labels:
            try:
                loc_ctx = storeroom_context.add_location(
                    location=label,
                    display_name=label,
                    svg_element_id=f"location-{label}",  # Temporary, will be updated in postprocessing
                    user_id=user_id
                )
                location_contexts.append(loc_ctx)
            except Exception as e:
                logger.warning(f"Failed to create location '{label}': {e}")
        
        if not location_contexts:
            raise ValueError("No locations were created from SVG labels")
        
        db.session.flush()
        
        # Postprocess SVG: update element IDs to database IDs, add onclick handlers
        try:
            postprocessed_svg = StoreroomFactory.postprocess_svg(
                processed_svg, 
                location_contexts, 
                location_or_bin="location"
            )
            storeroom_context.storeroom.svg_content = postprocessed_svg
            
            # Update svg_element_ids in locations to match new prefixed database IDs
            for loc_ctx in location_contexts:
                loc_ctx.location.svg_element_id = f"location-{loc_ctx.location_id}"
            
            db.session.flush()
        except Exception as e:
            logger.warning(f"SVG postprocessing failed: {e}")
        
        logger.info(
            f"Created storeroom with SVG layout: {storeroom_context.storeroom.room_name} "
            f"(ID: {storeroom_context.storeroom.id}) with {len(location_contexts)} locations"
        )
        
        return storeroom_context
    
    @staticmethod
    def create_storeroom_location(storeroom_id: int, form_fields: Dict[str, Any],
                                  user_id: Optional[int] = None) -> LocationContext:
        """
        Create a new location in a storeroom from form fields.
        
        Args:
            storeroom_id: ID of the storeroom
            form_fields: Dictionary containing:
                - location: Location identifier (required)
                - display_name: Optional display name
            user_id: ID of user creating the location
            
        Returns:
            LocationContext for the created location
            
        Raises:
            ValueError: If required fields are missing or storeroom doesn't exist
        """
        location = form_fields.get('location', '').strip()
        display_name = form_fields.get('display_name', '').strip()
        
        if not location:
            raise ValueError("Location identifier is required")
        
        storeroom_context = StoreroomContext(storeroom_id)
        
        location_context = storeroom_context.add_location(
            location=location,
            display_name=display_name or location,
            user_id=user_id
        )
        
        logger.info(f"Created location: {location} in storeroom {storeroom_id} (ID: {location_context.location_id})")
        
        return location_context
    
    @staticmethod
    def create_storeroom_location_from_svg(location_id: int, svg_xml: str,
                                          user_id: Optional[int] = None) -> LocationContext:
        """
        Add bin layout SVG to an existing location and create bins from it.
        
        Flow:
        1. Preprocess SVG (format, clean labels, validate)
        2. Get location context
        3. Create bins from cleaned labels
        4. Postprocess SVG (update IDs, onclick, data attributes)
        
        Args:
            location_id: ID of the location
            svg_xml: SVG XML content for bin layout
            user_id: ID of user creating the bins
            
        Returns:
            LocationContext for the location
            
        Raises:
            ValueError: If SVG parsing fails or location doesn't exist
        """
        # Preprocess SVG: format, clean labels, validate uniqueness
        try:
            processed_svg, bin_labels = StoreroomFactory.preprocess_svg(svg_xml, location_or_bin="bin")
        except ValueError as e:
            raise ValueError(f"SVG preprocessing failed: {e}")
        
        # Get location context
        location_context = LocationContext(location_id)
        
        # Store processed SVG
        location_context.location.bin_layout_svg = processed_svg
        db.session.flush()
        
        # Create bins from cleaned labels
        bin_contexts = []
        for label in bin_labels:
            try:
                bin_obj = location_context.add_bin(
                    bin_tag=label,
                    svg_element_id=f"bin-{label}",  # Temporary, will be updated in postprocessing
                    user_id=user_id
                )
                # Create a wrapper object for postprocessing (matches LocationContext interface)
                from types import SimpleNamespace
                location_wrapper = SimpleNamespace()
                location_wrapper.location = label
                bin_context = BinContextWrapper(
                    location=location_wrapper,
                    location_id=bin_obj.id
                )
                bin_contexts.append(bin_context)
            except ValueError as e:
                # Bin might already exist - skip it
                logger.debug(f"Skipped bin '{label}': {e}")
        
        if not bin_contexts:
            raise ValueError("No bins were created from SVG labels")
        
        db.session.flush()
        
        # Postprocess SVG: update element IDs to database IDs, add onclick handlers
        try:
            postprocessed_svg = StoreroomFactory.postprocess_svg(
                processed_svg,
                bin_contexts,  # BinContextWrapper matches LocationContext interface
                location_or_bin="bin"
            )
            location_context.location.bin_layout_svg = postprocessed_svg
            
            # Update svg_element_ids in bins to match new prefixed database IDs
            for bin_context in bin_contexts:
                bin_obj = location_context.get_bin(bin_context.location_id)
                if bin_obj:
                    bin_obj.svg_element_id = f"bin-{bin_context.location_id}"
            
            db.session.flush()
        except Exception as e:
            logger.warning(f"SVG postprocessing failed: {e}")
        
        logger.info(
            f"Added bin layout to location {location_id}: "
            f"{len(bin_contexts)} bins created"
        )
        
        return location_context
