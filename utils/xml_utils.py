"""XML utility functions for reading sections based on strategy."""
import xml.etree.ElementTree as ET
from typing import List, Optional, Set
from utils.logger import logger


def read_xml_section(
    file_path: str, 
    target_elements: List[str], 
    context_elements: Optional[List[str]] = None
) -> str:
    """
    Read specific XML sections by element type, preserving context.
    
    Uses streaming parser to extract only needed sections without loading
    the entire file into memory.
    
    Args:
        file_path: Path to the XML file
        target_elements: List of element tag names to extract
        context_elements: Optional list of element tags to include for context
        
    Returns:
        XML string containing the requested sections
    """
    target_set = set(target_elements)
    context_set = set(context_elements) if context_elements else set()
    
    # Track what we're collecting
    collected_elements = []
    element_stack = []
    current_element = None
    current_content = []
    in_target = False
    in_context = False
    
    try:
        for event, elem in ET.iterparse(file_path, events=('start', 'end')):
            if event == 'start':
                element_stack.append(elem.tag)
                
                # Check if we're entering a target or context element
                if elem.tag in target_set:
                    in_target = True
                    current_element = elem.tag
                    current_content = []
                elif elem.tag in context_set:
                    in_context = True
                    current_element = elem.tag
                    current_content = []
            
            elif event == 'end':
                tag = elem.tag
                
                # If we're in a target or context element, collect it
                if in_target and tag == current_element:
                    # Serialize this element
                    elem_str = ET.tostring(elem, encoding='unicode')
                    collected_elements.append(elem_str)
                    in_target = False
                    current_element = None
                elif in_context and tag == current_element:
                    # Serialize context element
                    elem_str = ET.tostring(elem, encoding='unicode')
                    collected_elements.append(elem_str)
                    in_context = False
                    current_element = None
                
                # Clean up
                if element_stack:
                    element_stack.pop()
                elem.clear()  # Free memory immediately
        
        # Combine all collected elements
        result = '\n'.join(collected_elements)
        
        if not result:
            logger.warning(f"No elements found for {target_elements} in {file_path}")
            # Fallback: try to read file and extract manually
            return _fallback_read_sections(file_path, target_elements, context_elements)
        
        return result
        
    except Exception as e:
        logger.error(f"Error reading XML section: {e}")
        # Fallback to simpler method
        return _fallback_read_sections(file_path, target_elements, context_elements)


def _fallback_read_sections(
    file_path: str,
    target_elements: List[str],
    context_elements: Optional[List[str]]
) -> str:
    """
    Fallback method: read file and extract sections using findall.
    Less memory efficient but more reliable for complex XML.
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        collected = []
        
        # Find target elements (handle namespaces)
        for target in target_elements:
            # Try direct findall first
            elements = root.findall(f'.//{target}')
            if not elements:
                # Try with any namespace - iterate and match local name
                elements = [
                    elem for elem in root.iter()
                    if elem.tag.split('}')[-1] == target  # Get local name after namespace
                ]
            
            for elem in elements:
                collected.append(ET.tostring(elem, encoding='unicode'))
        
        # Find context elements
        if context_elements:
            for context in context_elements:
                elements = root.findall(f'.//{context}')
                if not elements:
                    # Try with any namespace
                    elements = [
                        elem for elem in root.iter()
                        if elem.tag.split('}')[-1] == context
                    ]
                
                for elem in elements:
                    collected.append(ET.tostring(elem, encoding='unicode'))
        
        return '\n'.join(collected)
        
    except Exception as e:
        logger.error(f"Fallback XML reading also failed: {e}")
        return ""

