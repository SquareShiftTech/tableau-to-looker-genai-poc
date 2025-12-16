"""XML utility functions - simple tools for agents."""
import os
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
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


def split_xml_file_recursive(
    file_path: str,
    output_dir: str,
    size_threshold: int = 500000,
    current_level: int = 0,
    max_levels: int = 10
) -> List[Dict[str, Any]]:
    """
    Recursively split XML file by element levels until all files ≤ size_threshold.
    
    Args:
        file_path: Path to XML file to split
        output_dir: Directory to save split files
        size_threshold: Maximum file size in bytes (default: 500KB)
        current_level: Current recursion level (prevent infinite loops)
        max_levels: Maximum recursion depth
    
    Returns:
        List of file metadata dicts: [{'file_path': '...', 'size_bytes': ...}, ...]
    """
    try:
        # Check file size
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return []
        
        file_size = os.path.getsize(file_path)
        
        # Edge case: Empty file
        if file_size == 0:
            logger.warning(f"Empty file: {file_path}, skipping")
            return []
        
        # Stop condition 1: File size ≤ threshold
        if file_size <= size_threshold:
            return [{
                'file_path': file_path,
                'size_bytes': file_size
            }]
        
        # Stop condition 2: Max recursion depth reached
        if current_level >= max_levels:
            logger.warning(
                f"Max recursion depth ({max_levels}) reached for {file_path} "
                f"(size: {file_size:,} bytes). Keeping file as-is."
            )
            return [{
                'file_path': file_path,
                'size_bytes': file_size
            }]
        
        # Parse XML to find child elements
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError as e:
            logger.error(f"Invalid XML in {file_path}: {e}. Keeping file as-is.")
            return [{
                'file_path': file_path,
                'size_bytes': file_size
            }]
        
        # Get child elements (next level)
        children = list(root)
        
        # Edge case: No child elements (single element, can't split further)
        if not children:
            logger.warning(
                f"Single XML element in {file_path} (size: {file_size:,} bytes). "
                f"Cannot split further. Keeping file as-is."
            )
            return [{
                'file_path': file_path,
                'size_bytes': file_size
            }]
        
        # Get base name for split files
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        base_ext = os.path.splitext(os.path.basename(file_path))[1] or '.xml'
        
        # Split into child elements
        split_files: List[Dict[str, Any]] = []
        child_index = 1
        
        for child in children:
            # Get child element tag name (handle namespaces)
            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            
            # Create filename: {base_name}_{index}.xml
            # For first split, use child tag name if it makes sense
            if current_level == 0:
                # Use child tag name (e.g., worksheet_1.xml, datasource_1.xml)
                split_filename = f"{child_tag}_{child_index}{base_ext}"
            else:
                # Use base name with index (e.g., worksheet_1_1.xml)
                split_filename = f"{base_name}_{child_index}{base_ext}"
            
            split_file_path = os.path.join(output_dir, split_filename)
            
            # Serialize child element to XML string
            child_xml = ET.tostring(child, encoding='unicode')
            
            # Add XML declaration if needed
            if not child_xml.startswith('<?xml'):
                child_xml = '<?xml version="1.0" encoding="utf-8"?>\n' + child_xml
            
            # Save child element to file
            try:
                with open(split_file_path, 'w', encoding='utf-8') as f:
                    f.write(child_xml)
                
                # Recursively check and split if needed
                recursive_files = split_xml_file_recursive(
                    split_file_path,
                    output_dir,
                    size_threshold=size_threshold,
                    current_level=current_level + 1,
                    max_levels=max_levels
                )
                
                split_files.extend(recursive_files)
                child_index += 1
                
            except Exception as e:
                logger.error(f"Error saving split file {split_file_path}: {e}")
                # Continue with next child
        
        # Remove original file if we successfully split it
        if split_files:
            try:
                os.remove(file_path)
                logger.info(f"Removed original file after splitting: {file_path}")
            except Exception as e:
                logger.warning(f"Could not remove original file {file_path}: {e}")
        
        return split_files
        
    except Exception as e:
        logger.error(f"Error in recursive splitting for {file_path}: {e}", exc_info=True)
        # On error, return original file
        if os.path.exists(file_path):
            return [{
                'file_path': file_path,
                'size_bytes': os.path.getsize(file_path)
            }]
        return []


def _parse_attribute_list(attr_str: str) -> List[str]:
    """
    Parse comma/and-separated attribute lists.
    
    Handles:
    - Backticks: `` `name`, `id` `` → ["name", "id"]
    - Plain: "name, caption, datatype" → ["name", "caption", "datatype"]
    - With "and": "name, caption, and type" → ["name", "caption", "type"]
    
    Args:
        attr_str: Attribute string to parse
    
    Returns:
        List of attribute names
    """
    # Remove backticks and single quotes if present
    attr_str = attr_str.replace('`', '').replace("'", '').strip()
    
    # Handle "name and caption" pattern (without comma)
    if ' and ' in attr_str and ',' not in attr_str:
        parts = attr_str.split(' and ')
        return [p.strip() for p in parts if p.strip()]
    
    # Split by comma first
    parts = re.split(r',\s*', attr_str)
    
    # Clean up each part
    attributes = []
    for part in parts:
        part = part.strip()
        if part:
            # Check if part contains "and" (e.g., "name and caption")
            if ' and ' in part:
                # Split on "and" as well
                and_parts = part.split(' and ')
                for ap in and_parts:
                    ap = ap.strip()
                    if ap:
                        attributes.append(ap)
            else:
                # Remove any remaining "and" at the start/end
                part = re.sub(r'^\s*and\s+', '', part)
                part = re.sub(r'\s+and\s*$', '', part)
                if part:
                    attributes.append(part)
    
    return attributes


def _parse_element_condition(elem_str: str) -> tuple[str, Dict[str, str]]:
    """
    Parse element with conditions: <zone type-v2="filter">
    
    Args:
        elem_str: Element string like "<zone type-v2=\"filter\">"
    
    Returns:
        Tuple of (element_name, conditions_dict)
    """
    # Extract element name
    match = re.search(r'<([\w-]+)', elem_str)
    if not match:
        return (elem_str, {})
    
    element_name = match.group(1)
    conditions = {}
    
    # Extract attribute conditions
    # Pattern: attribute="value" or attribute='value'
    attr_matches = re.findall(r'(\w+(?:-\w+)*)=["\']([^"\']+)["\']', elem_str)
    for attr_name, attr_value in attr_matches:
        conditions[attr_name] = attr_value
    
    return (element_name, conditions)


def _parse_path_specification(instruction: str) -> Optional[Dict[str, str]]:
    """
    Extract path from "within <X>", "from <X>/<Y>", "direct children of <X>", "directly under <X>", etc.
    
    Args:
        instruction: Full instruction string
    
    Returns:
        Dict with 'query' (XPath) and 'direct_children' (bool) or None
    """
    result = {'query': None, 'direct_children': False}
    
    # Pattern: "directly under <X>"
    match = re.search(r'directly\s+under\s+<([^>]+)>', instruction, re.IGNORECASE)
    if match:
        parent = match.group(1)
        result['query'] = f'.//{parent}'
        result['direct_children'] = True
        return result
    
    # Pattern: "direct children of <X>"
    match = re.search(r'direct\s+children\s+of\s+<([^>]+)>', instruction, re.IGNORECASE)
    if match:
        parent = match.group(1)
        result['query'] = f'.//{parent}'
        result['direct_children'] = True
        return result
    
    # Pattern: "within <X>"
    match = re.search(r'within\s+<([^>]+)>', instruction, re.IGNORECASE)
    if match:
        parent = match.group(1)
        result['query'] = f'.//{parent}'
        return result
    
    # Pattern: "from <X>/<Y>"
    match = re.search(r'from\s+<([^>]+)>/<([^>]+)>', instruction, re.IGNORECASE)
    if match:
        parent = match.group(1)
        child = match.group(2)
        result['query'] = f'.//{parent}//{child}'
        return result
    
    # Pattern: "in <X>"
    match = re.search(r'\bin\s+<([^>]+)>', instruction, re.IGNORECASE)
    if match:
        parent = match.group(1)
        result['query'] = f'.//{parent}'
        return result
    
    return None


def _extract_attributes_from_elements(
    elements: List[ET.Element],
    attributes: List[str]
) -> List[Dict[str, Any]]:
    """
    Extract specified attributes from element list.
    
    Args:
        elements: List of XML elements
        attributes: List of attribute names to extract
    
    Returns:
        List of dicts with extracted attributes: [{"name": "...", "id": "..."}, ...]
    """
    result = []
    for elem in elements:
        attrs_dict = {}
        for attr_name in attributes:
            value = elem.get(attr_name, '')
            if value:  # Only include non-empty attributes
                attrs_dict[attr_name] = value
        if attrs_dict:  # Only add if at least one attribute was found
            result.append(attrs_dict)
    return result


def _apply_conditions(
    elements: List[ET.Element],
    conditions: Dict[str, Optional[str]]
) -> List[ET.Element]:
    """
    Filter elements based on attribute conditions.
    
    Args:
        elements: List of XML elements to filter
        conditions: Dict of attribute conditions
                   - {"type-v2": "filter"} means element must have type-v2="filter"
                   - {"name": None} means element must have name attribute (any value)
    
    Returns:
        Filtered list of elements
    """
    if not conditions:
        return elements
    
    filtered = []
    for elem in elements:
        matches = True
        for attr_name, attr_value in conditions.items():
            elem_value = elem.get(attr_name)
            if attr_value is None:
                # Condition: attribute must exist (any value)
                if elem_value is None:
                    matches = False
                    break
            else:
                # Condition: attribute must equal specific value
                if elem_value != attr_value:
                    matches = False
                    break
        
        if matches:
            filtered.append(elem)
    
    return filtered


def _apply_exclusions(
    elements: List[ET.Element],
    exclusions: List[Dict[str, str]]
) -> List[ET.Element]:
    """
    Remove elements matching exclusion rules.
    
    Args:
        elements: List of XML elements to filter
        exclusions: List of exclusion conditions
                   - [{"type-v2": "filter"}] excludes elements with type-v2="filter"
    
    Returns:
        Filtered list of elements (exclusions removed)
    """
    if not exclusions:
        return elements
    
    filtered = []
    for elem in elements:
        should_exclude = False
        for exclusion in exclusions:
            matches_exclusion = True
            for attr_name, attr_value in exclusion.items():
                if elem.get(attr_name) != attr_value:
                    matches_exclusion = False
                    break
            if matches_exclusion:
                should_exclude = True
                break
        
        if not should_exclude:
            filtered.append(elem)
    
    return filtered


def _parse_instruction(instruction: str) -> Dict[str, Any]:
    """
    Parse natural language instruction to structured query.
    
    Enhanced to handle complex patterns:
    - Multiple attributes (with/without backticks)
    - Element conditions
    - Exclusions
    - Path specifications
    - Structure extraction
    
    Args:
        instruction: Natural language instruction
    
    Returns:
        Dict with pattern type, query details, attributes, conditions, exclusions
    """
    instruction_lower = instruction.lower()
    result = {
        'pattern': 'generic',
        'query': './/*',
        'attributes': [],
        'conditions': {},
        'exclusions': [],
        'path': None,
        'direct_children': False,
        'instruction': instruction
    }
    
    # Parse exclusions first (they appear at the end)
    exclusion_matches = re.findall(
        r'excluding\s+those\s+with\s+([\w-]+)=["\']([^"\']+)["\']',
        instruction,
        re.IGNORECASE
    )
    if exclusion_matches:
        result['exclusions'] = [{attr: val} for attr, val in exclusion_matches]
    
    # Parse "NOT" conditions with multiple values
    # "type-v2' is NOT 'layout-basic', 'layout-flow', 'title', or 'filter'"
    not_match = re.search(
        r"['\"]?([\w-]+)['\"]?\s+is\s+NOT\s+(.+)",
        instruction,
        re.IGNORECASE
    )
    if not_match:
        attr_name = not_match.group(1)
        not_values_str = not_match.group(2)
        
        # Extract all quoted values from the NOT clause
        # Pattern: 'layout-basic', 'layout-flow', 'title', or 'filter'
        # Stop at "Extract" or "." to avoid capturing too much
        not_values_str_clean = re.split(r'\s+Extract|\.', not_values_str)[0]  # Stop at "Extract" or "."
        not_values = re.findall(r"['\"]?([\w-]+)['\"]?", not_values_str_clean)
        
        # Add exclusions for each NOT value
        if not result.get('exclusions'):
            result['exclusions'] = []
        for val in not_values:
            result['exclusions'].append({attr_name: val})
    
    # Parse "and have a <attr> attribute" conditions (attribute must exist)
    have_attr_matches = re.findall(
        r'and\s+have\s+(?:a\s+)?[`\']?([\w-]+)[`\']?\s+attribute',
        instruction,
        re.IGNORECASE
    )
    if have_attr_matches:
        for attr_name in have_attr_matches:
            result['conditions'][attr_name] = None  # None means attribute must exist
    
    # Parse path specification
    path_info = _parse_path_specification(instruction)
    if path_info:
        result['path'] = path_info.get('query')
        result['direct_children'] = path_info.get('direct_children', False)
    
    # Pattern 1: Multiple attributes including text content
    # "Extract text content, `bold`, `fontcolor`, `fontsize` attributes from <run> elements"
    match = re.search(
        r'extract\s+text\s+content\s*,\s*([`\w\s,]+)\s+attributes?\s+from\s+<([^>]+)>\s+elements?',
        instruction,
        re.IGNORECASE
    )
    if match:
        attr_str = match.group(1)
        elem_str = match.group(2)
        attributes = _parse_attribute_list(attr_str)
        element_name, conditions = _parse_element_condition(f'<{elem_str}>')
        
        result['pattern'] = 'extract_attributes_with_text'
        result['attributes'] = attributes
        result['element'] = element_name
        result['include_text'] = True
        result['conditions'].update(conditions)
        
        # Build query
        if result['path']:
            result['query'] = f"{result['path']}//{element_name}"
        else:
            result['query'] = f'.//{element_name}'
        
        return result
    
    # Pattern 1.5: Nested path without spaces (check before other patterns)
    # "Extract 'bold', 'fontcolor', 'fontsize' attributes from <layout-options><title><formatted-text><run> element."
    # "Extract 'value' attribute from <style><style-rule element='table'><format attr='background-color'> element."
    # Find consecutive <X><Y><Z> patterns
    nested_elements = re.findall(r'<([\w-]+)', instruction)
    if len(nested_elements) >= 2:
        # Check if this is a nested path pattern (multiple consecutive elements)
        # Look for pattern like: "from <X><Y><Z> element" or "from <X attr='val'><Y> element"
        # Match: from <X>...<Y>...<Z>... element (allowing attributes in between)
        nested_path_match = re.search(
            r'from\s+<([\w-]+)(?:\s+[^>]+)?><([\w-]+)(?:\s+[^>]+)?><([\w-]+)(?:\s+[^>]+)?>(?:<([\w-]+)(?:\s+[^>]+)?>)?\s+element',
            instruction,
            re.IGNORECASE
        )
        if nested_path_match:
            # Extract element names (groups 1, 2, 3, 4)
            path_elements = []
            for i in range(1, 5):
                if nested_path_match.group(i):
                    path_elements.append(nested_path_match.group(i))
            
            if len(path_elements) >= 2:
                last_element = path_elements[-1]
                
                # Try to extract attributes mentioned before "from"
                attr_match = re.search(
                    r'extract\s+([`\'\w\s,-]+)\s+attributes?\s+from',
                    instruction,
                    re.IGNORECASE
                )
                if attr_match:
                    attr_str = attr_match.group(1)
                    attributes = _parse_attribute_list(attr_str)
                    
                    # Build nested XPath
                    nested_path = '//'.join(path_elements)
                    
                    result['pattern'] = 'extract_attributes' if len(attributes) > 1 else 'extract_attribute'
                    if len(attributes) > 1:
                        result['attributes'] = attributes
                    else:
                        result['attribute'] = attributes[0] if attributes else ''
                    result['element'] = last_element
                    result['query'] = f'.//{nested_path}'
                    
                    # Parse attribute conditions in path elements
                    # Check for element='table' in style-rule (parent condition)
                    elem_cond_match = re.search(r"<style-rule[^>]*element=['\"]?([\w-]+)['\"]?", instruction, re.IGNORECASE)
                    if elem_cond_match:
                        # Store as parent condition - will be applied to style-rule elements
                        result['parent_conditions'] = {'element': elem_cond_match.group(1)}
                    
                    # Check for attr='background-color' in format (child condition)
                    attr_cond_match = re.search(r"<format[^>]*attr=['\"]?([\w-]+)['\"]?", instruction, re.IGNORECASE)
                    if attr_cond_match:
                        # Store as condition on format element
                        result['conditions']['attr'] = attr_cond_match.group(1)
                    
                    return result
    
    # Pattern 2: Single attribute (simple) - MUST come before multiple attributes pattern
    # "Extract the class attribute from the <mark> element"
    # "Extract 'name' attribute from the <dashboard> element."
    # Check if it's a single attribute (not multiple)
    single_attr_match = re.search(
        r"extract\s+(?:the\s+)?[`'\"]?([\w-]+)[`'\"]?\s+attribute\s+from\s+(?:all\s+)?(?:the\s+)?<([^>]+)>\s+element(?:s)?\.?",
        instruction,
        re.IGNORECASE
    )
    # Make sure it's not multiple attributes (check if there's a comma or "and" before "attribute")
    if single_attr_match:
        before_attribute = instruction[:single_attr_match.start()].lower()
        # If there's a comma or "and" before "attribute", it's multiple attributes
        if ',' not in before_attribute and ' and ' not in before_attribute:
            attr_name = single_attr_match.group(1)
            element_name = single_attr_match.group(2)
            
            # Clean attribute name
            attr_name = attr_name.replace("'", '').replace('"', '').replace('`', '').strip()
            
            result['pattern'] = 'extract_attribute'
            result['attribute'] = attr_name
            result['element'] = element_name
            result['query'] = f'.//{element_name}'
            
            return result
    
    # Pattern 3: Multiple attributes with backticks or single quotes
    # "Extract `name`, `id`, `param`, `mode` attributes from <zone> elements"
    # "Extract 'derived-from', 'id', 'path', 'revision', 'site' attributes from the <repository-location> element."
    # "Extract 'name' and 'caption' attributes from all <datasource> elements directly under <datasources>."
    match = re.search(
        r'extract\s+([`\'\w\s,-]+)\s+attributes?\s+from\s+(?:all\s+)?(?:the\s+)?<([^>]+)>\s+element(?:s)?',
        instruction,
        re.IGNORECASE
    )
    if match:
        attr_str = match.group(1)
        elem_str = match.group(2)
        attributes = _parse_attribute_list(attr_str)
        element_name, conditions = _parse_element_condition(f'<{elem_str}>')
        
        result['pattern'] = 'extract_attributes'
        result['attributes'] = attributes
        result['element'] = element_name
        result['conditions'].update(conditions)
        
        # Check for "all" keyword
        if 'all' in instruction.lower():
            result['return_all'] = True
        
        # Build query
        if result['path']:
            if result.get('direct_children'):
                # For direct children, keep path separate - we'll handle in execution
                result['query'] = result['path']  # Parent path (e.g., .//datasources)
                # Element name is stored in result['element'] (e.g., 'datasource')
            else:
                result['query'] = f"{result['path']}//{element_name}"
        else:
            result['query'] = f'.//{element_name}'
        
        return result
    
    # Pattern 4: Multiple attributes without backticks (plain text)
    # "Extract name, caption, datatype, role, and type attributes from <column> elements"
    match = re.search(
        r'extract\s+([\w\s,-]+(?:and\s+[\w-]+)?)\s+attributes?\s+from\s+(?:all\s+)?(?:the\s+)?<([^>]+)>\s+element(?:s)?',
        instruction,
        re.IGNORECASE
    )
    if match:
        attr_str = match.group(1)
        elem_str = match.group(2)
        attributes = _parse_attribute_list(attr_str)
        element_name, conditions = _parse_element_condition(f'<{elem_str}>')
        
        result['pattern'] = 'extract_attributes'
        result['attributes'] = attributes
        result['element'] = element_name
        result['conditions'].update(conditions)
        
        # Check for "all" keyword
        if 'all' in instruction.lower():
            result['return_all'] = True
        
        # Build query
        if result['path']:
            if result.get('direct_children'):
                # For direct children, keep path separate
                result['query'] = result['path']  # Parent path
            else:
                result['query'] = f"{result['path']}//{element_name}"
        else:
            result['query'] = f'.//{element_name}'
        
        return result
    
    # Pattern 5: Single attribute with path
    # "Extract the class attribute from the <mark> element within <pane>"
    match = re.search(
        r'extract\s+(?:the\s+)?([\w-]+)\s+attribute\s+from\s+(?:the\s+)?<([^>]+)>\s+element\s+(?:within|in)\s+<([^>]+)>',
        instruction,
        re.IGNORECASE
    )
    if match:
        attr_name = match.group(1)
        element_name = match.group(2)
        parent_name = match.group(3)
        
        result['pattern'] = 'extract_attribute'
        result['attribute'] = attr_name
        result['element'] = element_name
        result['query'] = f'.//{parent_name}//{element_name}'
        
        return result
    
    
    # Pattern 7: Extract all elements
    # "Extract all <X> elements" or "Find all <X> elements"
    match = re.search(r'(?:extract|find)\s+all\s+<([^>]+)>\s+elements?', instruction_lower)
    if match:
        element_name = match.group(1)
        result['pattern'] = 'extract_all_elements'
        result['element'] = element_name
        result['query'] = f'.//{element_name}'
        return result
    
    # Pattern 8: Extract all elements within/inside another element
    match = re.search(r'(?:extract|find)\s+all\s+<([^>]+)>\s+elements?\s+(?:within|inside|in)\s+<([^>]+)>', instruction_lower)
    if match:
        child_element = match.group(1)
        parent_element = match.group(2)
        result['pattern'] = 'extract_all_elements'
        result['element'] = child_element
        result['query'] = f'.//{parent_element}//{child_element}'
        return result
    
    # Pattern 9: Extract structure with attributes
    # "Extract the hierarchical structure of <zones> elements, including their id, name, type-v2, x, y, h, w attributes"
    match = re.search(
        r'extract\s+(?:the\s+)?(?:hierarchical\s+)?structure\s+of\s+<([^>]+)>\s+elements?.*?including\s+their\s+([\w\s,]+(?:and\s+[\w]+)?)\s+attributes?',
        instruction,
        re.IGNORECASE
    )
    if match:
        element_name = match.group(1)
        attr_str = match.group(2)
        attributes = _parse_attribute_list(attr_str)
        
        result['pattern'] = 'extract_structure'
        result['element'] = element_name
        result['attributes'] = attributes
        result['query'] = f'.//{element_name}'
        return result
    
    # Pattern 10: Extract structure (simple)
    match = re.search(r'(?:extract|get)\s+<([^>]+)>\s+structure', instruction_lower)
    if match:
        element_name = match.group(1)
        result['pattern'] = 'extract_structure'
        result['element'] = element_name
        result['query'] = f'.//{element_name}'
        return result
    
    # Pattern 11: Find...Extract pattern
    # "Find <zone> elements... Extract 'name' and 'id'."
    # "Find <zone> elements (in main dashboard and device layouts) where 'type-v2=\"filter\"'. Extract 'name', 'id', 'mode', 'param'."
    match = re.search(
        r'find\s+<([^>]+)>\s+elements?.*?extract\s+([`\'\w\s,-]+)',
        instruction,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        element_name = match.group(1)
        attr_str = match.group(2)
        attributes = _parse_attribute_list(attr_str)
        
        result['pattern'] = 'extract_attributes'
        result['attributes'] = attributes
        result['element'] = element_name
        result['query'] = f'.//{element_name}'
        
        # Parse conditions from "where" clause
        where_match = re.search(r"where\s+['\"]?([\w-]+)['\"]?=['\"]?([^'\"]+)['\"]?", instruction, re.IGNORECASE)
        if where_match:
            attr_name = where_match.group(1)
            attr_value = where_match.group(2)
            result['conditions'][attr_name] = attr_value
        
        # Parse "that have a 'name' attribute" condition
        have_attr_match = re.search(r"that\s+have\s+(?:a\s+)?['\"]?([\w-]+)['\"]?\s+attribute", instruction, re.IGNORECASE)
        if have_attr_match:
            attr_name = have_attr_match.group(1)
            result['conditions'][attr_name] = None  # Must exist
        
        return result
    
    # Pattern 12: Find references
    match = re.search(r'find\s+<([^>]+)>\s+references?(?:\s+in\s+<([^>]+)>)?', instruction_lower)
    if match:
        element_name = match.group(1)
        parent_element = match.group(2) if match.group(2) else None
        result['pattern'] = 'find_references'
        result['element'] = element_name
        if parent_element:
            result['query'] = f'.//{parent_element}//{element_name}'
        else:
            result['query'] = f'.//{element_name}'
        return result
    
    # Pattern 12: Check for elements
    match = re.search(r'check\s+(?:for|if)\s+<([^>]+)>\s+elements?', instruction_lower)
    if match:
        element_name = match.group(1)
        result['pattern'] = 'check_for'
        result['element'] = element_name
        result['query'] = f'.//{element_name}'
        return result
    
    # Pattern 13: Extract elements and their expressions
    # "Extract <filter> elements and their expressions from <groupfilter> members"
    match = re.search(
        r'extract\s+<([^>]+)>\s+elements?\s+and\s+their\s+(\w+)\s+from',
        instruction,
        re.IGNORECASE
    )
    if match:
        element_name = match.group(1)
        attr_name = match.group(2)  # e.g., "expressions"
        result['pattern'] = 'extract_elements_with_attr'
        result['element'] = element_name
        result['attribute'] = attr_name
        result['query'] = f'.//{element_name}'
        return result
    
    # Pattern 14: Text content extraction
    # "Extract the text content of <field> elements"
    match = re.search(
        r'extract\s+(?:the\s+)?text\s+content\s+of\s+<([^>]+)>\s+elements?',
        instruction,
        re.IGNORECASE
    )
    if match:
        element_name = match.group(1)
        result['pattern'] = 'extract_text_content'
        result['element'] = element_name
        result['query'] = f'.//{element_name}'
        return result
    
    # Pattern 15: "For...extract...and...from" pattern
    # "For the <datasource-dependencies> block, extract 'name', 'caption', 'datatype', 'role', 'type' from <column> elements and 'column', 'derivation', 'name', 'pivot', 'type' from <column-instance> elements."
    for_match = re.search(
        r'for\s+(?:the\s+)?<([\w-]+)>\s+block.*?extract\s+([`\'\w\s,-]+)\s+from\s+<([\w-]+)>\s+elements?\s+and\s+([`\'\w\s,-]+)\s+from\s+<([\w-]+)>\s+elements?',
        instruction,
        re.IGNORECASE | re.DOTALL
    )
    if for_match:
        block_name = for_match.group(1)
        attr_str1 = for_match.group(2)
        elem1 = for_match.group(3)
        attr_str2 = for_match.group(4)
        elem2 = for_match.group(5)
        
        # This is complex - extract from two element types
        # For now, extract from first element type (can be enhanced later)
        attributes1 = _parse_attribute_list(attr_str1)
        
        result['pattern'] = 'extract_attributes'
        result['attributes'] = attributes1
        result['element'] = elem1
        result['query'] = f'.//{block_name}//{elem1}'
        result['instruction'] = instruction  # Keep original for reference
        return result
    
    # Pattern 16: Complex instruction with multiple parts
    # "Extract name, caption, datatype, role, and type attributes from <column> elements, and name, column, derivation, pivot, type from <column-instance> elements, all within <datasource-dependencies>"
    if 'and' in instruction_lower and 'attributes' in instruction_lower and 'from' in instruction_lower:
        # Try to parse as multi-element attribute extraction
        # Extract first part before "and"
        first_part_match = re.search(
            r'extract\s+([`\'\w\s,-]+)\s+attributes?\s+from\s+<([\w-]+)>\s+elements?',
            instruction,
            re.IGNORECASE
        )
        if first_part_match:
            attr_str = first_part_match.group(1)
            elem_str = first_part_match.group(2)
            attributes = _parse_attribute_list(attr_str)
            element_name, conditions = _parse_element_condition(f'<{elem_str}>')
            
            result['pattern'] = 'extract_attributes'
            result['attributes'] = attributes
            result['element'] = element_name
            result['conditions'].update(conditions)
            result['query'] = f'.//{element_name}'
            return result
    
    # Default: return generic with instruction preserved
    result['pattern'] = 'generic'
    result['instruction'] = instruction
    return result


def _execute_instruction(root_elem: ET.Element, parsed_instruction: Dict[str, Any]) -> Any:
    """
    Execute parsed instruction on XML element and return structured data.
    
    Args:
        root_elem: Root XML element to query
        parsed_instruction: Parsed instruction dict from _parse_instruction()
    
    Returns:
        Structured data (dicts/lists) instead of XML strings
    """
    pattern = parsed_instruction.get('pattern')
    query = parsed_instruction.get('query', '')
    
    try:
        if pattern == 'extract_attributes' or pattern == 'extract_attributes_with_text':
            # Extract multiple attributes from elements (optionally with text content)
            # Handle direct children if specified
            direct_children = parsed_instruction.get('direct_children', False)
            if direct_children:
                # For direct children, find parent first, then get direct children
                parent_query = parsed_instruction.get('path', '')
                element_name = parsed_instruction.get('element', '')
                
                if parent_query and element_name:
                    # Find parent elements
                    parents = root_elem.findall(parent_query)
                    elements = []
                    for parent in parents:
                        # Get direct children only (not descendants)
                        for child in parent:
                            # Handle namespaces
                            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                            if child_tag == element_name:
                                elements.append(child)
                else:
                    # Fallback: try to get direct children from query
                    # If query is like ".//datasources", get direct children
                    if query.startswith('.//'):
                        parent_tag = query.replace('.//', '')
                        parents = root_elem.findall(f'.//{parent_tag}')
                        elements = []
                        for parent in parents:
                            for child in parent:
                                child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                                if child_tag == element_name:
                                    elements.append(child)
                    else:
                        elements = []
            else:
                elements = root_elem.findall(query)
            
            if not elements:
                return []
            
            # Apply conditions
            conditions = parsed_instruction.get('conditions', {})
            if conditions:
                elements = _apply_conditions(elements, conditions)
            
            # Apply exclusions
            exclusions = parsed_instruction.get('exclusions', [])
            if exclusions:
                elements = _apply_exclusions(elements, exclusions)
            
            # Extract attributes
            attributes = parsed_instruction.get('attributes', [])
            # Clean attribute names (remove quotes)
            attributes = [attr.replace("'", '').replace('"', '').replace('`', '').strip() for attr in attributes if attr]
            include_text = parsed_instruction.get('include_text', False) or (pattern == 'extract_attributes_with_text')
            
            if attributes:
                result = _extract_attributes_from_elements(elements, attributes)
                # Add text content if requested
                if include_text:
                    for i, elem in enumerate(elements):
                        if elem.text and elem.text.strip():
                            if i < len(result):
                                result[i]['_text'] = elem.text.strip()
                return result
            else:
                # If no specific attributes, extract all attributes from each element
                result = []
                for elem in elements:
                    attrs_dict = dict(elem.attrib)
                    if include_text and elem.text and elem.text.strip():
                        attrs_dict['_text'] = elem.text.strip()
                    if attrs_dict:
                        result.append(attrs_dict)
                return result
        
        elif pattern == 'extract_attribute':
            # Extract single attribute
            element_name = parsed_instruction.get('element', '')
            conditions = parsed_instruction.get('conditions', {})
            
            # Check if root_elem itself matches the element we're looking for
            root_tag = root_elem.tag.split('}')[-1] if '}' in root_elem.tag else root_elem.tag
            if root_tag == element_name:
                # Root element is the target - use it directly
                elements = [root_elem]
            else:
                # For nested paths with parent conditions, filter intermediate elements
                # Example: <style><style-rule element='table'><format attr='background-color'>
                parent_conditions = parsed_instruction.get('parent_conditions', {})
                if parent_conditions:
                    # Find parent elements first (e.g., style-rule with element='table')
                    # Extract parent path from query (everything except last element)
                    query_parts = query.split('//')
                    if len(query_parts) > 1:
                        parent_query = '//'.join(query_parts[:-1])  # All but last
                        parent_elements = root_elem.findall(parent_query)
                        parent_elements = _apply_conditions(parent_elements, parent_conditions)
                        
                        # Now find child elements within filtered parents
                        last_element = query_parts[-1]
                        elements = []
                        for parent in parent_elements:
                            child_elements = parent.findall(f'.//{last_element}')
                            if conditions:
                                child_elements = _apply_conditions(child_elements, conditions)
                            elements.extend(child_elements)
                    else:
                        # Fallback to regular search
                        elements = root_elem.findall(query)
                        if conditions:
                            elements = _apply_conditions(elements, conditions)
                else:
                    # Regular search
                    elements = root_elem.findall(query)
                    if conditions:
                        elements = _apply_conditions(elements, conditions)
            
            if not elements:
                return None
            
            attr_name = parsed_instruction.get('attribute', '')
            # Remove quotes if present
            if attr_name:
                attr_name = attr_name.replace("'", '').replace('"', '').replace('`', '').strip()
            
            if not attr_name:
                return None
            
            # Check if "all" keyword is present - always return list
            instruction_text = parsed_instruction.get('instruction', '').lower()
            return_all = 'all' in instruction_text
            
            # Extract values
            values = [elem.get(attr_name, '') for elem in elements if elem.get(attr_name)]
            if not values:
                return None
            elif return_all or len(values) > 1:
                return values
            else:
                return values[0]
        
        elif pattern == 'extract_all_elements':
            # Extract all elements with all their attributes
            elements = root_elem.findall(query)
            if not elements:
                return []
            
            result = []
            for elem in elements:
                attrs_dict = dict(elem.attrib)
                # Also include text content if present
                if elem.text and elem.text.strip():
                    attrs_dict['_text'] = elem.text.strip()
                if attrs_dict:
                    result.append(attrs_dict)
            return result
        
        elif pattern == 'extract_structure':
            # Extract hierarchical structure
            elements = root_elem.findall(query)
            if not elements:
                return None
            
            attributes = parsed_instruction.get('attributes', [])
            
            def build_structure(elem: ET.Element) -> Dict[str, Any]:
                """Recursively build structure for element and children."""
                struct = {}
                
                # Extract specified attributes or all attributes
                if attributes:
                    for attr in attributes:
                        value = elem.get(attr, '')
                        if value:
                            struct[attr] = value
                else:
                    struct.update(dict(elem.attrib))
                
                # Include text content
                if elem.text and elem.text.strip():
                    struct['_text'] = elem.text.strip()
                
                # Recursively process children
                children = list(elem)
                if children:
                    child_list = []
                    for child in children:
                        child_struct = build_structure(child)
                        if child_struct:
                            child_list.append(child_struct)
                    if child_list:
                        struct['_children'] = child_list
                
                return struct
            
            if len(elements) == 1:
                return build_structure(elements[0])
            else:
                return [build_structure(elem) for elem in elements]
        
        elif pattern == 'extract_elements_with_attr':
            # Extract elements and a specific attribute/child
            elements = root_elem.findall(query)
            if not elements:
                return []
            
            attr_name = parsed_instruction.get('attribute', '')
            result = []
            for elem in elements:
                item = dict(elem.attrib)
                # Try to find child element or attribute with the name
                child = elem.find(f'.//{attr_name}')
                if child is not None:
                    if child.text:
                        item[attr_name] = child.text.strip()
                    else:
                        item[attr_name] = dict(child.attrib)
                elif elem.get(attr_name):
                    item[attr_name] = elem.get(attr_name)
                result.append(item)
            return result
        
        elif pattern == 'extract_attributes_complex':
            # Complex multi-element extraction - try manual parsing
            instruction = parsed_instruction.get('instruction', '')
            # For now, return empty and log - this needs special handling
            logger.warning(f"Complex instruction not fully handled: {instruction[:100]}")
            return []
        
        elif pattern == 'find_references':
            # Find references (extract name/id/caption)
            elements = root_elem.findall(query)
            refs = []
            for elem in elements:
                ref_id = elem.get('name') or elem.get('id') or elem.get('caption', '')
                if ref_id:
                    refs.append(ref_id)
            return refs
        
        elif pattern == 'check_for':
            # Check if element exists
            element = root_elem.find(query)
            return element is not None
        
        elif pattern == 'generic':
            # Generic fallback - try to extract something useful
            instruction = parsed_instruction.get('instruction', '')
            
            # Try to find any element mentioned
            elem_matches = re.findall(r'<([\w-]+)>', instruction)
            if elem_matches:
                # Try to find the first element mentioned
                element_name = elem_matches[0]
                elements = root_elem.findall(f'.//{element_name}')
                if elements:
                    # Extract all attributes from first element
                    if len(elements) == 1:
                        return dict(elements[0].attrib)
                    else:
                        return [dict(elem.attrib) for elem in elements]
            
            return None
        
        else:
            # Unknown pattern - try generic approach
            elements = root_elem.findall(query)
            if elements:
                if len(elements) == 1:
                    return dict(elements[0].attrib)
                else:
                    return [dict(elem.attrib) for elem in elements]
            return None
    
    except Exception as e:
        logger.warning(f"Error executing instruction {pattern}: {e}", exc_info=True)
        return None


def extract_features_from_xml(
    file_path: str,
    component_id: str,
    parsing_instructions: Dict[str, str],
    feature_catalog: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract features from XML using parsing instructions.
    
    Uses pattern matching to convert natural language instructions to XML queries.
    Falls back to feature_catalog parsing_guidance if pattern matching fails.
    
    Args:
        file_path: Path to XML file
        component_id: Component ID to extract (for finding specific component in file)
        parsing_instructions: Dict of feature_name -> instruction string
        feature_catalog: Optional feature catalog with parsing_guidance fallback
    
    Returns:
        Dict with extracted features
    """
    features = {}
    
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return features
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Find component by ID/name if needed
        component_elem = root
        if component_id:
            # Clean component_id (remove braces if present)
            clean_id = component_id.strip('{}')
            
            # For dashboards, the XML structure is: <dashboards><dashboard name="...">
            # The component_id is a GUID, but XML might only have name attribute
            # Try to find by matching the component name from discovered_components
            
            # First, try to find by exact ID match
            found = False
            for elem in root.iter():
                elem_id = elem.get('id', '')
                if elem_id and (component_id == elem_id or clean_id in elem_id or elem_id in component_id):
                    component_elem = elem
                    found = True
                    break
            
            # If not found by ID, try to find by element type
            # For dashboards, look for <dashboard> element
            if not found:
                # Check if this is a dashboard file - look for dashboard element
                dashboard_elem = root.find('.//dashboard')
                if dashboard_elem is not None:
                    component_elem = dashboard_elem
                    found = True
                
                # For worksheets, look for worksheet with matching name/id
                elif root.find('.//worksheet') is not None:
                    # Try to find worksheet by name or id
                    for worksheet in root.findall('.//worksheet'):
                        ws_name = worksheet.get('name', '')
                        ws_id = worksheet.get('id', '')
                        if component_id in ws_name or component_id in ws_id or ws_name in component_id:
                            component_elem = worksheet
                            found = True
                            break
                
                # For datasources, look for datasource element
                elif root.find('.//datasource') is not None:
                    datasource_elem = root.find('.//datasource')
                    if datasource_elem is not None:
                        component_elem = datasource_elem
                        found = True
        
        # Extract each feature using parsing instructions
        for feature_name, instruction in parsing_instructions.items():
            # Tier 1: Try pattern matching on instruction
            parsed_instruction = _parse_instruction(instruction)
            value = _execute_instruction(component_elem, parsed_instruction)
            
            # Tier 2: If pattern matching failed, try feature_catalog fallback
            if value is None and feature_catalog:
                catalog_guidance = feature_catalog.get('parsing_guidance', {}).get(feature_name)
                if catalog_guidance:
                    parsed_instruction = _parse_instruction(catalog_guidance)
                    value = _execute_instruction(component_elem, parsed_instruction)
            
            # Tier 3: If still None, log warning
            if value is None:
                logger.warning(f"Could not extract feature '{feature_name}' from {file_path}")
                features[feature_name] = None
            else:
                features[feature_name] = value
        
        return features
    
    except Exception as e:
        logger.error(f"Error extracting features from {file_path}: {e}", exc_info=True)
        return features


def extract_structure_from_xml(
    file_path: str,
    component_id: str,
    component_type: str
) -> Dict[str, Any]:
    """
    Extract structure (layout, hierarchy, relationships) from XML.
    
    Args:
        file_path: Path to XML file
        component_id: Component ID
        component_type: Type of component (dashboard, worksheet, datasource, calculation, filter, parameter)
    
    Returns:
        Dict with structure information
    """
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return {}
    
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Find component element
        component_elem = root
        if component_id:
            for elem in root.iter():
                elem_id = elem.get('id') or elem.get('name') or ''
                if component_id in elem_id or elem_id in component_id:
                    component_elem = elem
                    break
        
        # Call component-specific extractor
        if component_type == 'dashboard':
            return extract_dashboard_structure(component_elem, component_id)
        elif component_type == 'worksheet':
            return extract_worksheet_structure(component_elem, component_id)
        elif component_type == 'datasource':
            return extract_datasource_structure(component_elem, component_id)
        elif component_type == 'calculation':
            return extract_calculation_structure(component_elem, component_id)
        elif component_type == 'filter':
            return extract_filter_structure(component_elem, component_id)
        elif component_type == 'parameter':
            return extract_parameter_structure(component_elem, component_id)
        else:
            logger.warning(f"Unknown component type: {component_type}")
            return {}
    
    except Exception as e:
        logger.error(f"Error extracting structure from {file_path}: {e}", exc_info=True)
        return {}


def extract_dashboard_structure(xml_elem: ET.Element, dashboard_id: str) -> Dict[str, Any]:
    """Extract dashboard structure: zones, layout, filters, parameters."""
    structure = {
        'layout_type': 'single_zone',
        'zones': [],
        'filters': {'count': 0, 'locations': []},
        'parameters': {'count': 0, 'used_in': []}
    }
    
    try:
        # Find zones
        zones = xml_elem.findall('.//zone')
        if not zones:
            zones = xml_elem.findall('.//Zone')
        
        zone_list = []
        for zone in zones:
            zone_id = zone.get('id', '')
            zone_name = zone.get('name', '')
            zone_type = zone.get('type', '')
            
            # Get position
            x = int(zone.get('x', 0))
            y = int(zone.get('y', 0))
            w = int(zone.get('w', 0))
            h = int(zone.get('h', 0))
            
            zone_info = {
                'id': zone_id,
                'name': zone_name,
                'type': zone_type,
                'position': {'x': x, 'y': y, 'w': w, 'h': h}
            }
            
            # Check for worksheet references
            worksheets = zone.findall('.//worksheet')
            if worksheets:
                zone_info['worksheets'] = [ws.get('name') or ws.get('id', '') for ws in worksheets]
            
            # Check for filter references
            filters = zone.findall('.//filter')
            if filters:
                zone_info['filters'] = [f.get('name') or f.get('id', '') for f in filters]
                structure['filters']['locations'].append(f'zone_{zone_id}')
            
            # Check for parameter references
            params = zone.findall('.//parameter')
            if params:
                zone_info['parameters'] = [p.get('name') or p.get('id', '') for p in params]
                structure['parameters']['used_in'].append(f'zone_{zone_id}')
            
            zone_list.append(zone_info)
        
        structure['zones'] = zone_list
        structure['layout_type'] = 'multi_zone' if len(zone_list) > 1 else 'single_zone'
        
        # Count filters and parameters
        all_filters = xml_elem.findall('.//filter')
        structure['filters']['count'] = len(all_filters)
        
        all_params = xml_elem.findall('.//parameter')
        structure['parameters']['count'] = len(all_params)
    
    except Exception as e:
        logger.warning(f"Error extracting dashboard structure: {e}")
    
    return structure


def extract_worksheet_structure(xml_elem: ET.Element, worksheet_id: str) -> Dict[str, Any]:
    """Extract worksheet structure: chart type, data fields, marks."""
    structure = {
        'chart_type': 'unknown',
        'data_fields': {
            'rows': [],
            'columns': [],
            'filters': []
        },
        'marks': {}
    }
    
    try:
        # Find view or table element
        view = xml_elem.find('.//view') or xml_elem.find('.//View')
        if not view:
            view = xml_elem
        
        # Extract chart type from mark
        mark = view.find('.//mark') or view.find('.//Mark')
        if mark is not None:
            mark_type = mark.get('type') or mark.get('class', 'unknown')
            structure['chart_type'] = mark_type
            structure['marks'] = {'type': mark_type}
        
        # Extract rows
        rows = view.findall('.//row') or view.findall('.//Row')
        for row in rows:
            col = row.find('.//column') or row.find('.//Column')
            if col is not None:
                field_name = col.get('name') or col.get('caption', '')
                field_type = col.get('type', 'dimension')
                structure['data_fields']['rows'].append({
                    'name': field_name,
                    'type': field_type
                })
        
        # Extract columns
        cols = view.findall('.//col') or view.findall('.//Col')
        for col_elem in cols:
            col = col_elem.find('.//column') or col_elem.find('.//Column')
            if col is not None:
                field_name = col.get('name') or col.get('caption', '')
                field_type = col.get('type', 'measure')
                aggregation = col.get('aggregation', '')
                structure['data_fields']['columns'].append({
                    'name': field_name,
                    'type': field_type,
                    'aggregation': aggregation
                })
        
        # Extract filters
        filters = view.findall('.//filter') or view.findall('.//Filter')
        for filt in filters:
            field_name = filt.get('name') or filt.get('field', '')
            field_type = filt.get('type', 'dimension')
            structure['data_fields']['filters'].append({
                'name': field_name,
                'type': field_type
            })
    
    except Exception as e:
        logger.warning(f"Error extracting worksheet structure: {e}")
    
    return structure


def extract_datasource_structure(xml_elem: ET.Element, datasource_id: str) -> Dict[str, Any]:
    """Extract datasource structure: connection, tables, fields."""
    structure = {
        'connection': {},
        'tables': []
    }
    
    try:
        # Extract connection
        conn = xml_elem.find('.//connection') or xml_elem.find('.//Connection')
        if conn is not None:
            conn_class = conn.get('class', '')
            structure['connection'] = {
                'type': conn_class,
                'server': conn.get('server', ''),
                'dbname': conn.get('dbname', ''),
                'project': conn.get('project', ''),
                'schema': conn.get('schema', '')
            }
        
        # Extract tables/relations
        relations = xml_elem.findall('.//relation') or xml_elem.findall('.//Relation')
        for rel in relations:
            table_name = rel.get('name', '')
            table_type = rel.get('type', '')
            
            # Extract fields from this table
            fields = []
            for col in rel.findall('.//column') or rel.findall('.//Column'):
                field_name = col.get('name', '')
                field_type = col.get('type', '')
                fields.append({
                    'name': field_name,
                    'type': field_type
                })
            
            structure['tables'].append({
                'name': table_name,
                'type': table_type,
                'fields': fields
            })
    
    except Exception as e:
        logger.warning(f"Error extracting datasource structure: {e}")
    
    return structure


def extract_calculation_structure(xml_elem: ET.Element, calculation_id: str) -> Dict[str, Any]:
    """Extract calculation structure: formula, dependencies."""
    structure = {
        'formula': '',
        'formula_structure': {},
        'dependencies': {
            'fields_used': [],
            'functions_used': []
        },
        'data_type': '',
        'aggregation': 'none'
    }
    
    try:
        # Find calculation element
        calc = xml_elem.find('.//calculation') or xml_elem.find('.//Calculation')
        if calc is not None:
            formula = calc.get('formula', '')
            structure['formula'] = formula
            
            # Simple formula structure parsing
            if '/' in formula:
                structure['formula_structure'] = {'type': 'division'}
            elif '*' in formula:
                structure['formula_structure'] = {'type': 'multiplication'}
            elif '+' in formula:
                structure['formula_structure'] = {'type': 'addition'}
            elif '-' in formula:
                structure['formula_structure'] = {'type': 'subtraction'}
            
            # Extract field references (simple pattern: [FieldName])
            field_refs = re.findall(r'\[([^\]]+)\]', formula)
            structure['dependencies']['fields_used'] = list(set(field_refs))
            
            # Extract function references
            functions = re.findall(r'(\w+)\s*\(', formula)
            structure['dependencies']['functions_used'] = list(set(functions))
        
        # Get data type from column element
        col = xml_elem.find('.//column') or xml_elem.find('.//Column')
        if col is not None:
            structure['data_type'] = col.get('type') or col.get('datatype', '')
            structure['aggregation'] = col.get('aggregation', 'none')
    
    except Exception as e:
        logger.warning(f"Error extracting calculation structure: {e}")
    
    return structure


def extract_filter_structure(xml_elem: ET.Element, filter_id: str) -> Dict[str, Any]:
    """Extract filter structure: type, field, expression, applied_to, scope."""
    structure = {
        'filter_type': '',
        'field': '',
        'expression': '',
        'applied_to': {
            'worksheets': [],
            'dashboards': []
        },
        'scope': 'worksheet'
    }
    
    try:
        # Find filter element
        filt = xml_elem.find('.//filter') or xml_elem.find('.//Filter')
        if filt is not None:
            structure['filter_type'] = filt.get('type', 'dimension')
            structure['field'] = filt.get('name') or filt.get('field', '')
            
            # Extract expression
            expr = filt.find('.//expression') or filt.find('.//Expression')
            if expr is not None:
                structure['expression'] = expr.text or ''
            
            # Check for members (for dimension filters)
            members = filt.findall('.//member') or filt.findall('.//Member')
            if members:
                member_list = [m.get('value') or m.text for m in members if m.get('value') or m.text]
                structure['expression'] = ', '.join(member_list)
        
        # Determine scope (worksheet, dashboard, global)
        # This would need to be determined from context, defaulting to worksheet
        structure['scope'] = 'worksheet'
    
    except Exception as e:
        logger.warning(f"Error extracting filter structure: {e}")
    
    return structure


def extract_parameter_structure(xml_elem: ET.Element, parameter_id: str) -> Dict[str, Any]:
    """Extract parameter structure: type, default value, allowed values, used_by, scope."""
    structure = {
        'parameter_type': '',
        'data_type': '',
        'default_value': '',
        'allowed_values': None,
        'used_by': {
            'dashboards': [],
            'worksheets': [],
            'calculations': []
        },
        'scope': 'workbook'
    }
    
    try:
        # Find parameter element
        param = xml_elem.find('.//parameter') or xml_elem.find('.//Parameter')
        if param is not None:
            structure['parameter_type'] = param.get('type', '')
            structure['data_type'] = param.get('datatype', '')
            structure['default_value'] = param.get('value') or param.get('default', '')
            
            # Extract allowed values
            allowed = param.findall('.//allowed-value') or param.findall('.//AllowedValue')
            if allowed:
                structure['allowed_values'] = [v.get('value') or v.text for v in allowed if v.get('value') or v.text]
        
        # Scope would be determined from context
        structure['scope'] = 'workbook'
    
    except Exception as e:
        logger.warning(f"Error extracting parameter structure: {e}")
    
    return structure
