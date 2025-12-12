"""Dashboard Agent - Step 3c: Analyze dashboards."""
import os
import json
from typing import List, Dict, Any
from datetime import datetime
from models.state import AssessmentState
from services.bigquery_service import bigquery_service
from utils.logger import logger


def _assess_complexity(features: Dict[str, Any], dependencies: Dict[str, Any]) -> str:
    """Assess dashboard complexity based on features and dependencies."""
    complexity_score = 0
    
    # Charts count
    charts_count = features.get('charts_count', 0)
    if charts_count > 10:
        complexity_score += 2
    elif charts_count > 5:
        complexity_score += 1
    
    # Filters count
    filters_count = features.get('filters_count', 0)
    if filters_count > 5:
        complexity_score += 1
    
    # Interactivity
    interactivity = features.get('interactivity', [])
    if len(interactivity) > 2:
        complexity_score += 1
    
    # Dependencies
    worksheets_count = len(dependencies.get('worksheets', []))
    datasources_count = len(dependencies.get('datasources', []))
    if worksheets_count > 5 or datasources_count > 3:
        complexity_score += 1
    
    if complexity_score >= 4:
        return 'high'
    elif complexity_score >= 2:
        return 'medium'
    else:
        return 'low'


async def dashboard_agent(state: AssessmentState) -> AssessmentState:
    """
    Dashboard Agent - Analyze dashboard structure and complexity.
    
    INPUT: state with parsed_dashboards
    OUTPUT: state with dashboard_analysis populated
    WRITES: BigQuery table "dashboards"
    """
    
    logger.info("Starting dashboard agent")
    
    parsed_dashboards = state.get('parsed_dashboards', [])
    if not parsed_dashboards:
        logger.warning("No parsed dashboards found, skipping dashboard analysis")
        state['dashboard_analysis'] = []
        state['status'] = 'analysis_complete'
        return state
    
    job_id = state.get('job_id', 'unknown')
    created_at = datetime.utcnow().isoformat() + 'Z'
    
    # Process each parsed dashboard
    analysis: List[Dict[str, Any]] = []
    
    for dashboard in parsed_dashboards:
        workbook_name = dashboard.get('workbook_name', 'unknown')
        dashboard_id = dashboard.get('id', '')
        dashboard_name = dashboard.get('name', 'unnamed_dashboard')
        features = dashboard.get('features', {})
        dependencies = dashboard.get('dependencies', {})
        
        # Assess complexity
        complexity = _assess_complexity(features, dependencies)
        
        # Build analysis record
        record = {
            'workbook_name': workbook_name,
            'name': dashboard_name,
            'id': dashboard_id,
            'features': features,
            'complexity': complexity,
            'dependencies': dependencies,
            'job_id': job_id,
            'created_at': created_at
        }
        
        analysis.append(record)
    
    logger.info(f"Analyzed {len(analysis)} dashboards")
    
    # Write to BigQuery (temporarily disabled)
    if analysis:
        bigquery_service.insert_rows("dashboards", analysis)
    
    # Write to JSON file
    output_dir = state.get('output_dir')
    if output_dir and analysis:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "dashboard_analysis.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Written {len(analysis)} dashboard analysis records to {output_file}")
    
    # Update state (only return fields we're modifying to avoid parallel update conflicts)
    logger.info("Completed dashboard agent")
    return {
        'dashboard_analysis': analysis
    }
