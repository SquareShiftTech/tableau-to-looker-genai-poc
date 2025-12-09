"""XML utility functions - simple tools for agents."""
import xml.etree.ElementTree as ET
from typing import List
from utils.logger import logger


def get_first_level_elements(file_path: str) -> List[str]:
    """
    Get direct children of root XML element.
    
    Args:
        file_path: Path to the XML file
        
    Returns:
        List of element names (e.g., ['datasources', 'worksheets', 'dashboards'])
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        first_level = []
        for child in root:
            # Handle namespaces - get local name after namespace
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag_name not in first_level:
                first_level.append(tag_name)
        logger.info(f"Found {len(first_level)} first-level elements: {first_level}")
        return first_level
    except Exception as e:
        logger.error(f"Error getting first-level elements: {e}")
        return []


def read_xml_element(file_path: str, element_name: str) -> str:
    """
    Simple tool: Read all instances of an XML element.
    
    Lightweight tool for agents to use. Reads all elements of the specified type
    from the XML file and returns them as a concatenated XML string.
    
    For first-level elements (direct children of root), this will find them correctly.
    
    Args:
        file_path: Path to the XML file
        element_name: Name of the XML element to read (e.g., "datasources", "worksheets")
        
    Returns:
        XML string containing all instances of the element, or empty string if not found
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # First, try to find as direct child of root (for first-level elements)
        elements = []
        for child in root:
            tag_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag_name == element_name:
                elements.append(child)
        
        # If not found as direct child, search all descendants
        if not elements:
            elements = root.findall(f'.//{element_name}')
        
        # If still not found, try with namespace handling (search all)
        if not elements:
            elements = [
                e for e in root.iter()
                if e.tag.split('}')[-1] == element_name  # Get local name after namespace
            ]
        
        if not elements:
            logger.warning(f"No elements found for '{element_name}' in {file_path}")
            return ""
        
        # Serialize all elements
        result = '\n'.join([ET.tostring(e, encoding='unicode') for e in elements])
        logger.info(f"Read {len(elements)} instances of '{element_name}' from {file_path}")
        return result
        
    except Exception as e:
        logger.error(f"Error reading element '{element_name}' from {file_path}: {e}")
        return ""
