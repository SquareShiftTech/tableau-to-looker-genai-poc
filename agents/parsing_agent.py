"""Parsing Agent - Step 2: Create dashboard assessment files."""
import os
import json
import re
from typing import Dict, Any, List, Optional
from models.state import AssessmentState
from utils.logger import logger


def _sanitize_filename(name: str) -> str:
    """Sanitize dashboard name for use in filename."""
    # Remove invalid characters and replace spaces with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = sanitized.lower()
    return sanitized[:100]  # Limit length


def _find_component_by_id(components: List[Dict[str, Any]], component_id: str) -> Optional[Dict[str, Any]]:
    """Find a component by its ID."""
    for component in components:
        if component.get('id') == component_id:
            return component
    return None


async def parsing_agent(state: AssessmentState) -> AssessmentState:
    """
    Parsing Agent - Create one file per dashboard with all related elements for assessment.
    
    INPUT: state with discovered_components (component catalog from Exploration Agent)
    OUTPUT: state with parsed_dashboards populated
    WRITES: output/{job_id}/assessments/dashboard_{name}.json (one file per dashboard)
    
    Process:
    1. Read discovered_components from state (component catalog)
    2. For each dashboard in catalog:
       - Get dashboard details
       - Resolve related worksheets, datasources, filters, parameters, calculations
       - Extract only assessment-relevant properties
       - Save to output/{job_id}/assessments/dashboard_{name}.json
    """
    
    logger.info("Starting parsing agent")
    
    discovered_components = state.get('discovered_components', {})
    if not discovered_components:
        logger.warning("No discovered components found, skipping parsing")
        state['status'] = 'parsing_complete'
        return state
    
    output_dir = state.get('output_dir')
    if not output_dir:
        logger.warning("No output directory found, skipping file creation")
        state['status'] = 'parsing_complete'
        return state
    
    # Create assessments directory
    assessments_dir = os.path.join(output_dir, 'assessments')
    os.makedirs(assessments_dir, exist_ok=True)
    logger.info(f"Created assessments directory: {assessments_dir}")
    
    # Get component catalog
    dashboards = discovered_components.get('dashboards', [])
    worksheets = discovered_components.get('worksheets', [])
    datasources = discovered_components.get('datasources', [])
    filters = discovered_components.get('filters', [])
    parameters = discovered_components.get('parameters', [])
    calculations = discovered_components.get('calculations', [])
    
    # Create index maps for quick lookup
    worksheets_map = {w.get('id'): w for w in worksheets if w.get('id')}
    datasources_map = {ds.get('id'): ds for ds in datasources if ds.get('id')}
    filters_map = {f.get('id'): f for f in filters if f.get('id')}
    parameters_map = {p.get('id'): p for p in parameters if p.get('id')}
    calculations_map = {c.get('id'): c for c in calculations if c.get('id')}
    
    parsed_dashboards: List[Dict[str, Any]] = []
    
    # Process each dashboard
    for dashboard in dashboards:
        dashboard_id = dashboard.get('id')
        dashboard_name = dashboard.get('name', 'unnamed_dashboard')
        
        logger.info(f"Processing dashboard: {dashboard_name} (id: {dashboard_id})")
        
        # Resolve related worksheets
        worksheet_ids = dashboard.get('worksheets', [])
        related_worksheets = []
        for ws_id in worksheet_ids:
            ws = worksheets_map.get(ws_id)
            if ws:
                # Extract assessment-relevant properties only
                related_worksheets.append({
                    'id': ws.get('id'),
                    'name': ws.get('name'),
                    'type': ws.get('type'),
                    'calculations_count': len(ws.get('calculations', [])),
                    'filters_count': len(ws.get('filters', [])),
                    'datasources_count': len(ws.get('datasources', []))
                })
        
        # Resolve related datasources (from worksheets)
        datasource_ids = set()
        for ws_id in worksheet_ids:
            ws = worksheets_map.get(ws_id)
            if ws:
                datasource_ids.update(ws.get('datasources', []))
        
        related_datasources = []
        for ds_id in datasource_ids:
            ds = datasources_map.get(ds_id)
            if ds:
                related_datasources.append({
                    'id': ds.get('id'),
                    'name': ds.get('name'),
                    'type': ds.get('type'),
                    'calculations_count': len(ds.get('calculations', []))
                })
        
        # Resolve related filters
        filter_ids = dashboard.get('filters', [])
        related_filters = []
        for f_id in filter_ids:
            f = filters_map.get(f_id)
            if f:
                related_filters.append({
                    'id': f.get('id'),
                    'name': f.get('name'),
                    'type': f.get('type', f.get('datatype'))
                })
        
        # Resolve related parameters
        parameter_ids = dashboard.get('parameters', [])
        related_parameters = []
        for p_id in parameter_ids:
            p = parameters_map.get(p_id)
            if p:
                related_parameters.append({
                    'id': p.get('id'),
                    'name': p.get('name'),
                    'type': p.get('type', p.get('datatype')),
                    'default_value': p.get('default_value')
                })
        
        # Resolve related calculations (from worksheets)
        calculation_ids = set()
        for ws_id in worksheet_ids:
            ws = worksheets_map.get(ws_id)
            if ws:
                calculation_ids.update(ws.get('calculations', []))
        
        related_calculations = []
        for calc_id in calculation_ids:
            calc = calculations_map.get(calc_id)
            if calc:
                related_calculations.append({
                    'id': calc.get('id'),
                    'name': calc.get('name'),
                    'formula': calc.get('formula', calc.get('expression'))
                })
        
        # Build assessment file structure
        assessment_data = {
            'dashboard': {
                'id': dashboard_id,
                'name': dashboard_name,
                'title': dashboard.get('title', dashboard_name),
                'filters_count': len(related_filters),
                'interactivity': [],
                'charts_count': len(related_worksheets)
            },
            'related_worksheets': related_worksheets,
            'related_datasources': related_datasources,
            'filters': related_filters,
            'parameters': related_parameters,
            'calculations': related_calculations,
            'migration_complexity': {
                'overall': _assess_complexity(related_worksheets, related_calculations, related_filters),
                'factors': _identify_complexity_factors(related_worksheets, related_calculations, related_filters)
            }
        }
        
        # Add interactivity indicators
        if related_parameters:
            assessment_data['dashboard']['interactivity'].append('parameters')
        if len(related_filters) > 0:
            assessment_data['dashboard']['interactivity'].append('filters')
        if len(related_worksheets) > 1:
            assessment_data['dashboard']['interactivity'].append('multi_sheet')
        
        # Save to file
        sanitized_name = _sanitize_filename(dashboard_name)
        assessment_file = os.path.join(assessments_dir, f"dashboard_{sanitized_name}.json")
        
        with open(assessment_file, 'w', encoding='utf-8') as f:
            json.dump(assessment_data, f, indent=2)
        
        logger.info(f"Saved assessment file: {assessment_file}")
        
        # Add to parsed dashboards list
        parsed_dashboards.append({
            'id': dashboard_id,
            'name': dashboard_name,
            'assessment_file': assessment_file,
            'complexity': assessment_data['migration_complexity']['overall']
        })
    
    # Update state
    state['parsed_dashboards'] = parsed_dashboards
    state['status'] = 'parsing_complete'
    
    logger.info(f"Completed parsing agent - created {len(parsed_dashboards)} dashboard assessment files")
    return state


def _assess_complexity(
    worksheets: List[Dict[str, Any]],
    calculations: List[Dict[str, Any]],
    filters: List[Dict[str, Any]]
) -> str:
    """Assess overall migration complexity."""
    complexity_score = 0
    
    # Worksheets complexity
    if len(worksheets) > 5:
        complexity_score += 2
    elif len(worksheets) > 2:
        complexity_score += 1
    
    # Calculations complexity
    if len(calculations) > 10:
        complexity_score += 2
    elif len(calculations) > 5:
        complexity_score += 1
    
    # Filters complexity
    if len(filters) > 5:
        complexity_score += 1
    
    # Check for complex calculation formulas
    for calc in calculations:
        formula = calc.get('formula', '')
        if any(keyword in formula.lower() for keyword in ['window_', 'lod', 'table_calc', 'rank', 'running_']):
            complexity_score += 1
            break
    
    if complexity_score >= 4:
        return 'high'
    elif complexity_score >= 2:
        return 'medium'
    else:
        return 'low'


def _identify_complexity_factors(
    worksheets: List[Dict[str, Any]],
    calculations: List[Dict[str, Any]],
    filters: List[Dict[str, Any]]
) -> List[str]:
    """Identify specific complexity factors."""
    factors = []
    
    if len(worksheets) > 5:
        factors.append('many_worksheets')
    
    if len(calculations) > 10:
        factors.append('many_calculations')
    
    if len(filters) > 5:
        factors.append('many_filters')
    
    # Check for complex calculations
    for calc in calculations:
        formula = calc.get('formula', '')
        if 'window_' in formula.lower():
            factors.append('window_functions')
            break
        if 'lod' in formula.lower():
            factors.append('lod_expressions')
            break
    
    return factors

