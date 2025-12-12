"""Parsing Agent - Step 2: Extract detailed properties from components."""
import os
import json
import re
from typing import Dict, Any, List, Optional
from models.state import AssessmentState
from utils.logger import logger
from utils.xml_utils import read_xml_element


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


async def parsing_agent(state: AssessmentState) -> AssessmentState:
    """
    Parsing Agent - Extract detailed properties from component index.
    
    INPUT: state with discovered_components (component catalog from Exploration Agent)
    OUTPUT: state with parsed_dashboards, parsed_worksheets, parsed_datasources, parsed_calculations populated
    
    Process:
    1. Extract workbook_name from source_files
    2. Read XML files for detailed extraction based on component index
    3. Extract detailed properties: features, formulas, connection details, interactivity
    4. Store parsed data in state
    """
    
    logger.info("Starting parsing agent")
    
    discovered_components = state.get('discovered_components', {})
    if not discovered_components:
        logger.warning("No discovered components found, skipping parsing")
        state['parsed_dashboards'] = []
        state['parsed_worksheets'] = []
        state['parsed_datasources'] = []
        state['parsed_calculations'] = []
        state['status'] = 'parsing_complete'
        return state
    
    # Extract workbook_name
    source_files = state.get('source_files', [])
    workbook_name = _extract_workbook_name(source_files)
    logger.info(f"Extracted workbook_name: {workbook_name}")
    
    # Get parsed element paths for reading XML files
    parsed_elements_paths = state.get('parsed_elements_paths', [])
    elements_map = {e.get('element_name'): e.get('file_path') for e in parsed_elements_paths if e.get('file_path')}
    
    # Get component catalog
    dashboards_index = discovered_components.get('dashboards', [])
    worksheets_index = discovered_components.get('worksheets', [])
    datasources_index = discovered_components.get('datasources', [])
    calculations_index = discovered_components.get('calculations', [])
    filters_index = discovered_components.get('filters', [])
    parameters_index = discovered_components.get('parameters', [])
    
    # Create index maps for quick lookup
    worksheets_map = {w.get('id'): w for w in worksheets_index if w.get('id')}
    datasources_map = {ds.get('id'): ds for ds in datasources_index if ds.get('id')}
    filters_map = {f.get('id'): f for f in filters_index if f.get('id')}
    parameters_map = {p.get('id'): p for p in parameters_index if p.get('id')}
    calculations_map = {c.get('id'): c for c in calculations_index if c.get('id')}
    
    # Parse dashboards
    parsed_dashboards: List[Dict[str, Any]] = []
    for dashboard_idx in dashboards_index:
        dashboard_id = dashboard_idx.get('id')
        dashboard_name = dashboard_idx.get('name', 'unnamed_dashboard')
        
        logger.info(f"Processing dashboard: {dashboard_name} (id: {dashboard_id})")
        
        # Resolve dependencies
        worksheet_ids = dashboard_idx.get('worksheets', [])
        filter_ids = dashboard_idx.get('filters', [])
        parameter_ids = dashboard_idx.get('parameters', [])
        
        # Get related datasources from worksheets
        datasource_ids = set()
        for ws_id in worksheet_ids:
            ws = worksheets_map.get(ws_id)
            if ws:
                datasource_ids.update(ws.get('datasources', []))
        
        # Get related calculations from worksheets
        calculation_ids = set()
        for ws_id in worksheet_ids:
            ws = worksheets_map.get(ws_id)
            if ws:
                calculation_ids.update(ws.get('calculations', []))
        
        # Build features
        features = {
            'layout': 'multi_sheet' if len(worksheet_ids) > 1 else 'single_sheet',
            'filters_count': len(filter_ids),
            'interactivity': []
        }
        
        if parameter_ids:
            features['interactivity'].append('parameters')
        if filter_ids:
            features['interactivity'].append('filters')
        if len(worksheet_ids) > 1:
            features['interactivity'].append('multi_sheet')
        
        features['charts_count'] = len(worksheet_ids)
        
        # Build dependencies
        dependencies = {
            'worksheets': worksheet_ids,
            'datasources': list(datasource_ids),
            'filters': filter_ids,
            'parameters': parameter_ids
        }
        
        parsed_dashboards.append({
            'workbook_name': workbook_name,
            'id': dashboard_id,
            'name': dashboard_name,
            'features': features,
            'dependencies': dependencies
        })
    
    # Parse worksheets
    parsed_worksheets: List[Dict[str, Any]] = []
    for worksheet_idx in worksheets_index:
        worksheet_id = worksheet_idx.get('id')
        worksheet_name = worksheet_idx.get('name', 'unnamed_worksheet')
        
        logger.info(f"Processing worksheet: {worksheet_name} (id: {worksheet_id})")
        
        # Get dependencies
        datasource_ids = worksheet_idx.get('datasources', [])
        calculation_ids = worksheet_idx.get('calculations', [])
        filter_ids = worksheet_idx.get('filters', [])
        
        # Build features (basic - can be enhanced with LLM later)
        features = {
            'chart_type': worksheet_idx.get('type', 'unknown'),
            'calculations_count': len(calculation_ids),
            'filters_count': len(filter_ids),
            'interactivity': []
        }
        
        if filter_ids:
            features['interactivity'].append('filters')
        if calculation_ids:
            features['interactivity'].append('calculations')
        
        # Build dependencies
        dependencies = {
            'datasources': datasource_ids,
            'calculations': calculation_ids,
            'filters': filter_ids
        }
        
        parsed_worksheets.append({
            'id': worksheet_id,
            'name': worksheet_name,
            'features': features,
            'dependencies': dependencies
        })
    
    # Parse datasources
    parsed_datasources: List[Dict[str, Any]] = []
    datasources_file = elements_map.get('datasources')
    
    for datasource_idx in datasources_index:
        datasource_id = datasource_idx.get('id')
        datasource_name = datasource_idx.get('name', 'unnamed_datasource')
        
        logger.info(f"Processing datasource: {datasource_name} (id: {datasource_id})")
        
        # Try to read XML to extract type and connection details
        connection_details = {}
        datasource_type = 'unknown'
        
        if datasources_file and os.path.exists(datasources_file):
            try:
                # Read datasource XML section
                datasource_xml = read_xml_element(datasources_file, 'datasource')
                if datasource_xml:
                    # Try to extract type from XML (basic parsing)
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(f"<root>{datasource_xml}</root>")
                    
                    # Look for connection elements
                    for conn in root.findall('.//connection'):
                        conn_class = conn.get('class', '')
                        if 'bigquery' in conn_class.lower():
                            datasource_type = 'bigquery'
                            connection_details['project'] = conn.get('project', '')
                            connection_details['dataset'] = conn.get('schema', '')
                        elif 'sql' in conn_class.lower():
                            datasource_type = 'sql'
                            connection_details['server'] = conn.get('server', '')
                            connection_details['database'] = conn.get('dbname', '')
                        elif 'hyper' in conn_class.lower():
                            datasource_type = 'hyper'
                            connection_details['dbname'] = conn.get('dbname', '')
                        break
            except Exception as e:
                logger.warning(f"Error extracting datasource details for {datasource_name}: {e}")
        
        # Assess complexity (basic rule-based)
        complexity = 'low'
        calculation_count = len(datasource_idx.get('calculations', []))
        if calculation_count > 10:
            complexity = 'high'
        elif calculation_count > 5:
            complexity = 'medium'
        
        parsed_datasources.append({
            'id': datasource_id,
            'name': datasource_name,
            'type': datasource_type,
            'connection': connection_details,
            'complexity': complexity
        })
    
    # Parse calculations
    parsed_calculations: List[Dict[str, Any]] = []
    
    for calc_idx in calculations_index:
        calc_id = calc_idx.get('id')
        calc_name = calc_idx.get('name', 'unnamed_calculation')
        
        logger.info(f"Processing calculation: {calc_name} (id: {calc_id})")
        
        # Get datasource_id from relationships
        datasource_ids = calc_idx.get('related_datasources', [])
        datasource_id = datasource_ids[0] if datasource_ids else 'unknown'
        
        # Try to extract formula from XML
        formula = calc_idx.get('formula', calc_idx.get('expression', ''))
        
        # If no formula in index, extract from XML files
        if not formula:
            # Look for calculation in datasources XML (calculations are in <column> elements with <calculation> children)
            datasources_file = elements_map.get('datasources')
            if datasources_file and os.path.exists(datasources_file):
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(datasources_file)
                    root = tree.getroot()
                    
                    # Match by calculation ID (e.g., "[Calculation_14496010743898134]")
                    # The ID from discovered_components should match the column name attribute
                    for column in root.findall('.//column'):
                        column_name = column.get('name', '')
                        column_caption = column.get('caption', '')
                        
                        # Check if this column matches our calculation
                        # Priority: 1) Match by ID (column name), 2) Match by name (column caption)
                        matches = False
                        if calc_id:
                            # Remove brackets for comparison if needed
                            calc_id_clean = calc_id.strip('[]')
                            column_name_clean = column_name.strip('[]')
                            if calc_id == column_name or calc_id_clean in column_name_clean or calc_id in column_name:
                                matches = True
                        
                        if not matches and calc_name:
                            # Match by caption (the display name)
                            if calc_name == column_caption:
                                matches = True
                        
                        if matches:
                            # Find the calculation child element
                            calc_elem = column.find('.//calculation')
                            if calc_elem is not None:
                                formula = calc_elem.get('formula', '')
                                if formula:
                                    logger.debug(f"Found formula for {calc_name} (id: {calc_id}): {formula[:100]}...")
                                    break
                except Exception as e:
                    logger.warning(f"Error extracting formula from datasources XML for {calc_name} (id: {calc_id}): {e}")
        
        # Assess complexity based on formula
        complexity = 'low'
        if formula:
            formula_lower = formula.lower()
            if any(keyword in formula_lower for keyword in ['window_', 'lod', 'table_calc', 'rank', 'running_', 'lookup']):
                complexity = 'high'
            elif any(keyword in formula_lower for keyword in ['if', 'case', 'sum', 'avg', 'count']):
                complexity = 'medium'
        
        parsed_calculations.append({
            'datasource_id': datasource_id,
            'field_name': calc_name,
            'formula': formula,
            'complexity': complexity
        })
    
    # Write parsed data to JSON files
    output_dir = state.get('output_dir')
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
        if parsed_dashboards:
            dashboards_file = os.path.join(output_dir, "parsed_dashboards.json")
            with open(dashboards_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_dashboards, f, indent=2)
            logger.info(f"Written {len(parsed_dashboards)} parsed dashboards to {dashboards_file}")
        
        if parsed_worksheets:
            worksheets_file = os.path.join(output_dir, "parsed_worksheets.json")
            with open(worksheets_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_worksheets, f, indent=2)
            logger.info(f"Written {len(parsed_worksheets)} parsed worksheets to {worksheets_file}")
        
        if parsed_datasources:
            datasources_file = os.path.join(output_dir, "parsed_datasources.json")
            with open(datasources_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_datasources, f, indent=2)
            logger.info(f"Written {len(parsed_datasources)} parsed datasources to {datasources_file}")
        
        if parsed_calculations:
            calculations_file = os.path.join(output_dir, "parsed_calculations.json")
            with open(calculations_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_calculations, f, indent=2)
            logger.info(f"Written {len(parsed_calculations)} parsed calculations to {calculations_file}")
    
    # Update state
    state['parsed_dashboards'] = parsed_dashboards
    state['parsed_worksheets'] = parsed_worksheets
    state['parsed_datasources'] = parsed_datasources
    state['parsed_calculations'] = parsed_calculations
    state['status'] = 'parsing_complete'
    
    logger.info(f"Completed parsing agent:")
    logger.info(f"  - Parsed {len(parsed_dashboards)} dashboards")
    logger.info(f"  - Parsed {len(parsed_worksheets)} worksheets")
    logger.info(f"  - Parsed {len(parsed_datasources)} datasources")
    logger.info(f"  - Parsed {len(parsed_calculations)} calculations")
    
    return state
