"""Calculation Agent - Step 3a: Analyze calculations."""
import os
import json
from typing import List, Dict, Any
from datetime import datetime
from models.state import AssessmentState
from services.bigquery_service import bigquery_service
from utils.logger import logger


def _assess_complexity(formula: str) -> str:
    """Assess calculation complexity based on formula."""
    if not formula:
        return 'low'
    
    formula_lower = formula.lower()
    complexity_score = 0
    
    # Complex functions
    complex_keywords = ['window_', 'lod', 'table_calc', 'rank', 'running_', 'lookup', 'match']
    if any(keyword in formula_lower for keyword in complex_keywords):
        complexity_score += 2
    
    # Medium complexity functions
    medium_keywords = ['if', 'case', 'sum', 'avg', 'count', 'max', 'min']
    if any(keyword in formula_lower for keyword in medium_keywords):
        complexity_score += 1
    
    # Nested functions (indicated by multiple parentheses)
    if formula.count('(') > 3:
        complexity_score += 1
    
    # String operations
    if any(op in formula_lower for op in ['concat', 'split', 'replace', 'substring']):
        complexity_score += 1
    
    if complexity_score >= 3:
        return 'high'
    elif complexity_score >= 1:
        return 'medium'
    else:
        return 'low'


async def calculation_agent(state: AssessmentState) -> AssessmentState:
    """
    Calculation Agent - Analyze calculation complexity.
    
    INPUT: state with parsed_calculations
    OUTPUT: state with calculation_analysis populated
    WRITES: BigQuery table "calculation_fields"
    """
    
    logger.info("Starting calculation agent")
    
    parsed_calculations = state.get('parsed_calculations', [])
    if not parsed_calculations:
        logger.warning("No parsed calculations found, skipping calculation analysis")
        state['calculation_analysis'] = []
        state['status'] = 'analysis_complete'
        return state
    
    job_id = state.get('job_id', 'unknown')
    created_at = datetime.utcnow().isoformat() + 'Z'
    
    # Process each parsed calculation
    analysis: List[Dict[str, Any]] = []
    
    for calculation in parsed_calculations:
        datasource_id = calculation.get('datasource_id', 'unknown')
        field_name = calculation.get('field_name', 'unnamed_calculation')
        formula = calculation.get('formula', '')
        existing_complexity = calculation.get('complexity', 'low')
        
        # Use existing complexity or assess if not available
        if existing_complexity == 'low' and formula:
            complexity = _assess_complexity(formula)
        else:
            complexity = existing_complexity
        
        # Build analysis record
        record = {
            'datasource_id': datasource_id,
            'field_name': field_name,
            'formula': formula,
            'complexity': complexity,
            'job_id': job_id,
            'created_at': created_at
        }
        
        analysis.append(record)
    
    logger.info(f"Analyzed {len(analysis)} calculations")
    complexity_breakdown = {
        'low': sum(1 for a in analysis if a.get('complexity') == 'low'),
        'medium': sum(1 for a in analysis if a.get('complexity') == 'medium'),
        'high': sum(1 for a in analysis if a.get('complexity') == 'high')
    }
    logger.info(f"Complexity breakdown: {complexity_breakdown}")
    
    # Write to BigQuery (temporarily disabled)
    if analysis:
        bigquery_service.insert_rows("calculation_fields", analysis)
    
    # Write to JSON file
    output_dir = state.get('output_dir')
    if output_dir and analysis:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "calculation_analysis.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Written {len(analysis)} calculation analysis records to {output_file}")
    
    # Update state (only return fields we're modifying to avoid parallel update conflicts)
    logger.info("Completed calculation agent")
    return {
        'calculation_analysis': analysis
    }
