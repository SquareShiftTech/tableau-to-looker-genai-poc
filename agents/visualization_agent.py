"""Visualization Agent - Step 3b: Analyze worksheets (visualizations)."""
import os
import json
from typing import List, Dict, Any
from datetime import datetime
from models.state import AssessmentState
from services.bigquery_service import bigquery_service
from utils.logger import logger


def _assess_complexity(features: Dict[str, Any], dependencies: Dict[str, Any]) -> str:
    """Assess worksheet complexity based on features and dependencies."""
    complexity_score = 0
    
    # Calculations count
    calculations_count = features.get('calculations_count', 0)
    if calculations_count > 10:
        complexity_score += 2
    elif calculations_count > 5:
        complexity_score += 1
    
    # Filters count
    filters_count = features.get('filters_count', 0)
    if filters_count > 5:
        complexity_score += 1
    
    # Chart type complexity
    chart_type = features.get('chart_type', '').lower()
    complex_charts = ['heatmap', 'treemap', 'scatter', 'bubble', 'gantt']
    if any(ct in chart_type for ct in complex_charts):
        complexity_score += 1
    
    # Interactivity
    interactivity = features.get('interactivity', [])
    if len(interactivity) > 2:
        complexity_score += 1
    
    # Dependencies
    datasources_count = len(dependencies.get('datasources', []))
    if datasources_count > 2:
        complexity_score += 1
    
    if complexity_score >= 4:
        return 'high'
    elif complexity_score >= 2:
        return 'medium'
    else:
        return 'low'


async def visualization_agent(state: AssessmentState) -> AssessmentState:
    """
    Visualization Agent - Analyze worksheet structure and complexity.
    
    INPUT: state with parsed_worksheets
    OUTPUT: state with worksheet_analysis populated
    WRITES: BigQuery table "worksheets"
    """
    
    logger.info("Starting visualization agent (worksheets)")
    
    parsed_worksheets = state.get('parsed_worksheets', [])
    if not parsed_worksheets:
        logger.warning("No parsed worksheets found, skipping worksheet analysis")
        state['worksheet_analysis'] = []
        state['status'] = 'analysis_complete'
        return state
    
    job_id = state.get('job_id', 'unknown')
    created_at = datetime.utcnow().isoformat() + 'Z'
    
    # Process each parsed worksheet
    analysis: List[Dict[str, Any]] = []
    
    for worksheet in parsed_worksheets:
        worksheet_id = worksheet.get('id', '')
        worksheet_name = worksheet.get('name', 'unnamed_worksheet')
        features = worksheet.get('features', {})
        dependencies = worksheet.get('dependencies', {})
        
        # Assess complexity
        complexity = _assess_complexity(features, dependencies)
        
        # Build analysis record
        record = {
            'name': worksheet_name,
            'id': worksheet_id,
            'features': features,
            'complexity': complexity,
            'dependencies': dependencies,
            'job_id': job_id,
            'created_at': created_at
        }
        
        analysis.append(record)
    
    logger.info(f"Analyzed {len(analysis)} worksheets")
    
    # Write to BigQuery (temporarily disabled)
    if analysis:
        bigquery_service.insert_rows("worksheets", analysis)
    
    # Write to JSON file
    output_dir = state.get('output_dir')
    if output_dir and analysis:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "worksheet_analysis.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Written {len(analysis)} worksheet analysis records to {output_file}")
    
    # Update state (only return fields we're modifying to avoid parallel update conflicts)
    logger.info("Completed visualization agent")
    return {
        'worksheet_analysis': analysis,
        'visualization_analysis': analysis  # Backward compatibility
    }
