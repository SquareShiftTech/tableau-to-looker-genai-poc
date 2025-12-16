"""Parsing Agent - Step 2: Extract detailed properties from components."""
import os
import json
import re
from typing import Dict, Any, List, Optional
from models.state import AssessmentState
from utils.logger import logger
from utils.xml_utils import (
    extract_features_from_xml,
    extract_structure_from_xml
)


def _sanitize_filename(name: str) -> str:
    """Sanitize dashboard name for use in filename."""
    # Remove invalid characters and replace spaces with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = sanitized.lower()
    return sanitized[:100]  # Limit length


def _extract_workbook_name(source_files: List[Dict[str, str]]) -> str:
    """Extract workbook name from source files."""
    if not source_files:
        return "unknown_workbook"
    
    first_file = source_files[0]
    file_path = first_file.get('file_path', '')
    
    if not file_path:
        return "unknown_workbook"
    
    # Extract workbook name from file path
    basename = os.path.basename(file_path)
    # Remove extensions
    workbook_name = basename.replace('.twb', '').replace('.twbx', '').replace('.xml', '')
    
    return workbook_name or "unknown_workbook"


def load_feature_catalog(platform: str) -> Dict[str, Any]:
    """Load feature catalog for the given platform."""
    try:
        catalog_path = os.path.join("config", "feature_catalog.json")
        if not os.path.exists(catalog_path):
            logger.warning(f"Feature catalog not found: {catalog_path}")
            return {}
        
        with open(catalog_path, 'r', encoding='utf-8') as f:
            full_catalog = json.load(f)
        
        platform_catalog = full_catalog.get(platform, {})
        if not platform_catalog:
            logger.warning(f"No feature catalog found for platform: {platform}")
            return {}
        
        return platform_catalog
        
    except Exception as e:
        logger.error(f"Error loading feature catalog: {e}", exc_info=True)
        return {}


def create_file_map(parsed_elements_paths: List[Dict[str, Any]]) -> Dict[str, str]:
    """Create file map from parsed_elements_paths for quick lookup."""
    return {e.get('element_name'): e.get('file_path') for e in parsed_elements_paths if e.get('file_path')}


def extract_dependencies(component: Dict[str, Any], all_components: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[str]]:
    """Build dependency relationships for a component."""
    dependencies = {
        'worksheets': [],
        'datasources': [],
        'filters': [],
        'parameters': [],
        'calculations': []
    }
    
    # Extract from component relationships or direct references
    if 'worksheets' in component:
        dependencies['worksheets'] = component.get('worksheets', [])
    if 'datasources' in component:
        dependencies['datasources'] = component.get('datasources', [])
    if 'filters' in component:
        dependencies['filters'] = component.get('filters', [])
    if 'parameters' in component:
        dependencies['parameters'] = component.get('parameters', [])
    if 'calculations' in component:
        dependencies['calculations'] = component.get('calculations', [])
    
    return dependencies


def parse_dashboards(
    dashboards_index: List[Dict[str, Any]],
    file_map: Dict[str, str],
    workbook_name: str,
    feature_catalog: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Parse dashboard components with features and structure."""
    parsed = []
    
    for dashboard in dashboards_index:
        dashboard_id = dashboard.get('id', '')
        dashboard_name = dashboard.get('name', 'unnamed_dashboard')
        file_path = dashboard.get('file', '')
        parsing_instructions = dashboard.get('parsing_instructions', {})
        
        logger.info(f"Processing dashboard: {dashboard_name} (id: {dashboard_id})")
        
        # If file_path not in component, try to find it in file_map
        if not file_path or not os.path.exists(file_path):
            # Try to find dashboard file
            file_path = file_map.get('dashboards') or file_map.get('dashboard')
        
        features = {}
        structure = {}
        
        if file_path and os.path.exists(file_path):
            # Extract features using parsing_instructions
            catalog_guidance = feature_catalog.get('dashboard', {})
            features = extract_features_from_xml(
                file_path,
                dashboard_id,
                parsing_instructions,
                catalog_guidance
            )
            
            # Extract structure
            structure = extract_structure_from_xml(
                file_path,
                dashboard_id,
                'dashboard'
            )
        else:
            logger.warning(f"Dashboard file not found: {file_path}, using index data only")
            # Fallback to index data
            features = {
                'filters_count': len(dashboard.get('filters', [])),
                'worksheets_count': len(dashboard.get('worksheets', [])),
                'parameters_count': len(dashboard.get('parameters', []))
            }
            structure = {'layout_type': 'unknown'}
        
        # Build dependencies
        dependencies = extract_dependencies(dashboard, {})
        
        parsed.append({
            'workbook_name': workbook_name,
            'id': dashboard_id,
            'name': dashboard_name,
            'features': features,
            'structure': structure,
            'dependencies': dependencies
        })
    
    return parsed


def parse_worksheets(
    worksheets_index: List[Dict[str, Any]],
    file_map: Dict[str, str],
    feature_catalog: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Parse worksheet components with features and structure."""
    parsed = []
    
    for worksheet in worksheets_index:
        worksheet_id = worksheet.get('id', '')
        worksheet_name = worksheet.get('name', 'unnamed_worksheet')
        file_path = worksheet.get('file', '')
        parsing_instructions = worksheet.get('parsing_instructions', {})
        
        logger.info(f"Processing worksheet: {worksheet_name} (id: {worksheet_id})")
        
        # If file_path not in component, try to find it in file_map
        if not file_path or not os.path.exists(file_path):
            file_path = file_map.get('worksheets') or file_map.get('worksheet')
        
        features = {}
        structure = {}
        
        if file_path and os.path.exists(file_path):
            # Extract features using parsing_instructions
            catalog_guidance = feature_catalog.get('worksheet', {})
            features = extract_features_from_xml(
                file_path,
                worksheet_id,
                parsing_instructions,
                catalog_guidance
            )
            
            # Extract structure
            structure = extract_structure_from_xml(
                file_path,
                worksheet_id,
                'worksheet'
            )
        else:
            logger.warning(f"Worksheet file not found: {file_path}, using index data only")
            features = {
                'chart_type': worksheet.get('type', 'unknown'),
                'calculations_count': len(worksheet.get('calculations', [])),
                'filters_count': len(worksheet.get('filters', []))
            }
            structure = {'chart_type': 'unknown'}
        
        # Build dependencies
        dependencies = extract_dependencies(worksheet, {})
        
        parsed.append({
            'id': worksheet_id,
            'name': worksheet_name,
            'features': features,
            'structure': structure,
            'dependencies': dependencies
        })
    
    return parsed


def parse_datasources(
    datasources_index: List[Dict[str, Any]],
    file_map: Dict[str, str],
    feature_catalog: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Parse datasource components with features and structure."""
    parsed = []
    
    for datasource in datasources_index:
        datasource_id = datasource.get('id', '')
        datasource_name = datasource.get('name', 'unnamed_datasource')
        file_path = datasource.get('file', '')
        parsing_instructions = datasource.get('parsing_instructions', {})
        
        logger.info(f"Processing datasource: {datasource_name} (id: {datasource_id})")
        
        # If file_path not in component, try to find it in file_map
        if not file_path or not os.path.exists(file_path):
            file_path = file_map.get('datasources') or file_map.get('datasource')
        
        features = {}
        structure = {}
        
        if file_path and os.path.exists(file_path):
            # Extract features using parsing_instructions
            catalog_guidance = feature_catalog.get('datasource', {})
            features = extract_features_from_xml(
                file_path,
                datasource_id,
                parsing_instructions,
                catalog_guidance
            )
            
            # Extract structure
            structure = extract_structure_from_xml(
                file_path,
                datasource_id,
                'datasource'
            )
        else:
            logger.warning(f"Datasource file not found: {file_path}, using index data only")
            features = {
                'connection_type': 'unknown',
                'tables_count': len(datasource.get('tables', [])),
                'fields_count': len(datasource.get('fields', []))
            }
            structure = {'connection': {}, 'tables': []}
        
        parsed.append({
            'id': datasource_id,
            'name': datasource_name,
            'features': features,
            'structure': structure,
            'dependencies': extract_dependencies(datasource, {})
        })
    
    return parsed


def parse_calculations(
    calculations_index: List[Dict[str, Any]],
    file_map: Dict[str, str],
    feature_catalog: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Parse calculation components with features and structure."""
    parsed = []
    
    for calculation in calculations_index:
        calc_id = calculation.get('id', '')
        calc_name = calculation.get('name', 'unnamed_calculation')
        file_path = calculation.get('file', '')
        parsing_instructions = calculation.get('parsing_instructions', {})
        
        logger.info(f"Processing calculation: {calc_name} (id: {calc_id})")
        
        # Get datasource_id from relationships
        datasource_ids = calculation.get('related_datasources', [])
        datasource_id = datasource_ids[0] if datasource_ids else 'unknown'
        
        # If file_path not in component, try datasources file
        if not file_path or not os.path.exists(file_path):
            file_path = file_map.get('datasources') or file_map.get('datasource')
        
        features = {}
        structure = {}
        
        if file_path and os.path.exists(file_path):
            # Extract features using parsing_instructions
            catalog_guidance = feature_catalog.get('calculation', {})
            features = extract_features_from_xml(
                file_path,
                calc_id,
                parsing_instructions,
                catalog_guidance
            )
            
            # Extract structure
            structure = extract_structure_from_xml(
                file_path,
                calc_id,
                'calculation'
            )
        else:
            logger.warning(f"Calculation file not found: {file_path}, using index data only")
            formula = calculation.get('formula', calculation.get('expression', ''))
            features = {
                'formula': formula,
                'data_type': calculation.get('data_type', ''),
                'aggregation': calculation.get('aggregation', 'none')
            }
            structure = {
                'formula': formula,
                'formula_structure': {},
                'dependencies': {'fields_used': [], 'functions_used': []}
            }
        
        parsed.append({
            'datasource_id': datasource_id,
            'id': calc_id,
            'name': calc_name,
            'features': features,
            'structure': structure,
            'dependencies': extract_dependencies(calculation, {})
        })
    
    return parsed


def parse_filters(
    filters_index: List[Dict[str, Any]],
    file_map: Dict[str, str],
    feature_catalog: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Parse filter components with features and structure."""
    parsed = []
    
    for filter_comp in filters_index:
        filter_id = filter_comp.get('id', '')
        filter_name = filter_comp.get('name', 'unnamed_filter')
        file_path = filter_comp.get('file', '')
        parsing_instructions = filter_comp.get('parsing_instructions', {})
        
        logger.info(f"Processing filter: {filter_name} (id: {filter_id})")
        
        # If file_path not in component, try to find it in file_map
        if not file_path or not os.path.exists(file_path):
            # Filters might be in dashboards or worksheets files
            file_path = file_map.get('dashboards') or file_map.get('worksheets')
        
        features = {}
        structure = {}
        
        if file_path and os.path.exists(file_path):
            # Extract features using parsing_instructions
            catalog_guidance = feature_catalog.get('filter', {})
            features = extract_features_from_xml(
                file_path,
                filter_id,
                parsing_instructions,
                catalog_guidance
            )
            
            # Extract structure
            structure = extract_structure_from_xml(
                file_path,
                filter_id,
                'filter'
            )
        else:
            logger.warning(f"Filter file not found: {file_path}, using index data only")
            features = {
                'type': filter_comp.get('type', 'dimension'),
                'field': filter_comp.get('field', ''),
                'expression': filter_comp.get('expression', ''),
                'scope': filter_comp.get('scope', 'worksheet')
            }
            structure = {
                'filter_type': features['type'],
                'field': features['field'],
                'expression': features['expression'],
                'applied_to': {'worksheets': [], 'dashboards': []},
                'scope': features['scope']
            }
        
        # Build dependencies
        dependencies = extract_dependencies(filter_comp, {})
        
        parsed.append({
            'id': filter_id,
            'name': filter_name,
            'features': features,
            'structure': structure,
            'dependencies': dependencies
        })
    
    return parsed


def parse_parameters(
    parameters_index: List[Dict[str, Any]],
    file_map: Dict[str, str],
    feature_catalog: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Parse parameter components with features and structure."""
    parsed = []
    
    for parameter in parameters_index:
        param_id = parameter.get('id', '')
        param_name = parameter.get('name', 'unnamed_parameter')
        file_path = parameter.get('file', '')
        parsing_instructions = parameter.get('parsing_instructions', {})
        
        logger.info(f"Processing parameter: {param_name} (id: {param_id})")
        
        # If file_path not in component, try to find it in file_map
        if not file_path or not os.path.exists(file_path):
            # Parameters might be in dashboards or worksheets files
            file_path = file_map.get('dashboards') or file_map.get('worksheets')
        
        features = {}
        structure = {}
        
        if file_path and os.path.exists(file_path):
            # Extract features using parsing_instructions
            catalog_guidance = feature_catalog.get('parameter', {})
            features = extract_features_from_xml(
                file_path,
                param_id,
                parsing_instructions,
                catalog_guidance
            )
            
            # Extract structure
            structure = extract_structure_from_xml(
                file_path,
                param_id,
                'parameter'
            )
        else:
            logger.warning(f"Parameter file not found: {file_path}, using index data only")
            features = {
                'type': parameter.get('type', ''),
                'data_type': parameter.get('data_type', ''),
                'default_value': parameter.get('default_value', ''),
                'allowed_values': parameter.get('allowed_values')
            }
            structure = {
                'parameter_type': features['type'],
                'data_type': features['data_type'],
                'default_value': features['default_value'],
                'allowed_values': features['allowed_values'],
                'used_by': {'dashboards': [], 'worksheets': [], 'calculations': []},
                'scope': 'workbook'
            }
        
        # Build dependencies
        dependencies = extract_dependencies(parameter, {})
        
        parsed.append({
            'id': param_id,
            'name': param_name,
            'features': features,
            'structure': structure,
            'dependencies': dependencies
        })
    
    return parsed


def write_parsed_data(output_dir: str, parsed_data: Dict[str, List[Dict[str, Any]]]) -> None:
    """Write all parsed components to JSON files."""
    if not output_dir:
        logger.warning("No output directory specified, skipping file write")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    for component_type, components in parsed_data.items():
        if components:
            filename = f"{component_type}.json"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(components, f, indent=2)
            logger.info(f"Written {len(components)} {component_type} to {filepath}")


async def parsing_agent(state: AssessmentState) -> AssessmentState:
    """
    Parsing Agent - Extract features and structure from components.
    
    INPUT: discovered_components index from Exploration Agent
    OUTPUT: parsed_dashboards, parsed_worksheets, parsed_datasources, 
            parsed_calculations, parsed_filters, parsed_parameters
    
    Process:
    1. Get discovered_components index
    2. Create file map from parsed_elements_paths
    3. Load feature catalog
    4. Parse each component type (read XML files, extract features + structure)
    5. Write all parsed data to JSON files
    6. Update state
    """
    
    logger.info("Starting parsing agent")
    
    discovered_components = state.get('discovered_components', {})
    if not discovered_components:
        logger.warning("No discovered components found, skipping parsing")
        state['parsed_dashboards'] = []
        state['parsed_worksheets'] = []
        state['parsed_datasources'] = []
        state['parsed_calculations'] = []
        state['parsed_filters'] = []
        state['parsed_parameters'] = []
        state['status'] = 'parsing_complete'
        return state
    
    # Extract workbook_name
    source_files = state.get('source_files', [])
    workbook_name = _extract_workbook_name(source_files)
    logger.info(f"Extracted workbook_name: {workbook_name}")
    
    # Get platform
    platform = discovered_components.get('platform', 'tableau')
    if not platform and source_files:
        platform = source_files[0].get('platform', 'tableau')
    
    # Load feature catalog
    feature_catalog = load_feature_catalog(platform)
    
    # Get parsed element paths for reading XML files
    parsed_elements_paths = state.get('parsed_elements_paths', [])
    file_map = create_file_map(parsed_elements_paths)
    
    # Get component catalog (components are nested in discovered_components)
    # Handle both old structure (direct access) and new structure (nested in components)
    components = discovered_components.get('components', {})
    if not components:
        # Fallback to old structure (direct access)
        components = discovered_components
    
    dashboards_index = components.get('dashboards', [])
    worksheets_index = components.get('worksheets', [])
    datasources_index = components.get('datasources', [])
    calculations_index = components.get('calculations', [])
    filters_index = components.get('filters', [])
    parameters_index = components.get('parameters', [])
    
    # Parse each component type
    parsed_dashboards = parse_dashboards(dashboards_index, file_map, workbook_name, feature_catalog)
    parsed_worksheets = parse_worksheets(worksheets_index, file_map, feature_catalog)
    parsed_datasources = parse_datasources(datasources_index, file_map, feature_catalog)
    parsed_calculations = parse_calculations(calculations_index, file_map, feature_catalog)
    parsed_filters = parse_filters(filters_index, file_map, feature_catalog)
    parsed_parameters = parse_parameters(parameters_index, file_map, feature_catalog)
    
    # Write parsed data to JSON files
    output_dir = state.get('output_dir')
    write_parsed_data(output_dir, {
        'parsed_dashboards': parsed_dashboards,
        'parsed_worksheets': parsed_worksheets,
        'parsed_datasources': parsed_datasources,
        'parsed_calculations': parsed_calculations,
        'parsed_filters': parsed_filters,
        'parsed_parameters': parsed_parameters
    })
    
    # Update state
    state['parsed_dashboards'] = parsed_dashboards
    state['parsed_worksheets'] = parsed_worksheets
    state['parsed_datasources'] = parsed_datasources
    state['parsed_calculations'] = parsed_calculations
    state['parsed_filters'] = parsed_filters
    state['parsed_parameters'] = parsed_parameters
    state['status'] = 'parsing_complete'
    
    logger.info(f"Completed parsing agent:")
    logger.info(f"  - Parsed {len(parsed_dashboards)} dashboards")
    logger.info(f"  - Parsed {len(parsed_worksheets)} worksheets")
    logger.info(f"  - Parsed {len(parsed_datasources)} datasources")
    logger.info(f"  - Parsed {len(parsed_calculations)} calculations")
    logger.info(f"  - Parsed {len(parsed_filters)} filters")
    logger.info(f"  - Parsed {len(parsed_parameters)} parameters")
    
    return state
