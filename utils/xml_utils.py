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


def _parse_instruction(instruction: str) -> Dict[str, Any]:
    """
    Parse natural language instruction to structured query.
    
    Uses pattern matching to convert instructions to XPath-like queries.
    
    Args:
        instruction: Natural language instruction (e.g., "Extract all <filter> elements within <dashboard>")
    
    Returns:
        Dict with pattern type and query details
    """
    instruction_lower = instruction.lower()
    
    # Pattern 1: Extract all elements
    # "Extract all <X> elements" or "Find all <X> elements"
    match = re.search(r'(?:extract|find)\s+all\s+<([^>]+)>\s+elements', instruction_lower)
    if match:
        element_name = match.group(1)
        return {
            'pattern': 'extract_all_elements',
            'element': element_name,
            'query': f'.//{element_name}'
        }
    
    # Pattern 2: Extract all elements within/inside another element
    # "Extract all <X> elements within <Y>" or "Find all <X> in <Y>"
    match = re.search(r'(?:extract|find)\s+all\s+<([^>]+)>\s+elements?\s+(?:within|inside|in)\s+<([^>]+)>', instruction_lower)
    if match:
        child_element = match.group(1)
        parent_element = match.group(2)
        return {
            'pattern': 'extract_all_elements',
            'element': child_element,
            'query': f'.//{parent_element}//{child_element}'
        }
    
    # Pattern 3: Extract attribute
    # "Extract <X> element's Y attribute" or "Get <X> element's Y attribute"
    match = re.search(r'(?:extract|get)\s+<([^>]+)>\s+elements?\'?s?\s+(\w+)\s+attribute', instruction_lower)
    if match:
        element_name = match.group(1)
        attr_name = match.group(2)
        return {
            'pattern': 'extract_attribute',
            'element': element_name,
            'attribute': attr_name,
            'query': f'.//{element_name}'
        }
    
    # Pattern 4: Find references
    # "Find <X> references" or "Find <X> references in <Y>"
    match = re.search(r'find\s+<([^>]+)>\s+references?(?:\s+in\s+<([^>]+)>)?', instruction_lower)
    if match:
        element_name = match.group(1)
        parent_element = match.group(2) if match.group(2) else None
        if parent_element:
            query = f'.//{parent_element}//{element_name}'
        else:
            query = f'.//{element_name}'
        return {
            'pattern': 'find_references',
            'element': element_name,
            'query': query
        }
    
    # Pattern 5: Check for elements
    # "Check for <X> elements" or "Check if <X> exists"
    match = re.search(r'check\s+(?:for|if)\s+<([^>]+)>\s+elements?', instruction_lower)
    if match:
        element_name = match.group(1)
        return {
            'pattern': 'check_for',
            'element': element_name,
            'query': f'.//{element_name}'
        }
    
    # Pattern 6: Extract structure
    # "Extract <X> structure" or "Get <X> structure"
    match = re.search(r'(?:extract|get)\s+<([^>]+)>\s+structure', instruction_lower)
    if match:
        element_name = match.group(1)
        return {
            'pattern': 'extract_structure',
            'element': element_name,
            'query': f'.//{element_name}'
        }
    
    # Default: return generic query
    return {
        'pattern': 'generic',
        'query': instruction
    }


def _execute_instruction(root_elem: ET.Element, parsed_instruction: Dict[str, Any]) -> Any:
    """
    Execute parsed instruction on XML element.
    
    Args:
        root_elem: Root XML element to query
        parsed_instruction: Parsed instruction dict from _parse_instruction()
    
    Returns:
        Extracted value(s) based on instruction pattern
    """
    pattern = parsed_instruction.get('pattern')
    query = parsed_instruction.get('query', '')
    
    try:
        if pattern == 'extract_all_elements':
            elements = root_elem.findall(query)
            return [ET.tostring(e, encoding='unicode') for e in elements] if elements else []
        
        elif pattern == 'extract_attribute':
            element = root_elem.find(query)
            if element is not None:
                attr_name = parsed_instruction.get('attribute')
                return element.get(attr_name, '')
            return None
        
        elif pattern == 'find_references':
            elements = root_elem.findall(query)
            # Extract name or id attributes
            refs = []
            for elem in elements:
                ref_id = elem.get('name') or elem.get('id') or elem.get('caption', '')
                if ref_id:
                    refs.append(ref_id)
            return refs
        
        elif pattern == 'check_for':
            element = root_elem.find(query)
            return element is not None
        
        elif pattern == 'extract_structure':
            element = root_elem.find(query)
            if element is not None:
                return ET.tostring(element, encoding='unicode')
            return None
        
        else:
            # Generic: try to find element
            element = root_elem.find(query)
            if element is not None:
                return ET.tostring(element, encoding='unicode')
            return None
    
    except Exception as e:
        logger.warning(f"Error executing instruction {pattern}: {e}")
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
            # Try to find component element by id/name attribute
            for elem in root.iter():
                elem_id = elem.get('id') or elem.get('name') or ''
                if component_id in elem_id or elem_id in component_id:
                    component_elem = elem
                    break
        
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
