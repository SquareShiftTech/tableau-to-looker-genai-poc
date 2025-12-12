"""Data Source Agent - Step 3d: Analyze data sources."""
import os
import json
from typing import List, Dict, Any
from datetime import datetime
from models.state import AssessmentState
from services.bigquery_service import bigquery_service
from utils.logger import logger


def _assess_complexity(datasource_type: str, connection: Dict[str, Any]) -> str:
    """Assess datasource complexity based on type and connection details."""
    complexity_score = 0
    
    # Type complexity
    if datasource_type == 'hyper':
        complexity_score += 1  # Extract files can be complex
    elif datasource_type == 'sql':
        complexity_score += 1  # SQL connections can have joins, etc.
    elif datasource_type == 'bigquery':
        complexity_score += 0  # BigQuery is straightforward
    
    # Connection details complexity
    if connection:
        # Multiple tables or complex schemas indicate higher complexity
        if 'dataset' in connection and connection.get('dataset'):
            complexity_score += 0  # Dataset is normal
        if 'database' in connection and connection.get('database'):
            complexity_score += 0  # Database is normal
    
    if complexity_score >= 2:
        return 'high'
    elif complexity_score >= 1:
        return 'medium'
    else:
        return 'low'


async def datasource_agent(state: AssessmentState) -> AssessmentState:
    """
    Data Source Agent - Analyze data source compatibility and complexity.
    
    INPUT: state with parsed_datasources
    OUTPUT: state with datasource_analysis populated
    WRITES: BigQuery table "datasources"
    """
    
    logger.info("Starting datasource agent")
    
    parsed_datasources = state.get('parsed_datasources', [])
    if not parsed_datasources:
        logger.warning("No parsed datasources found, skipping datasource analysis")
        state['datasource_analysis'] = []
        state['status'] = 'analysis_complete'
        return state
    
    job_id = state.get('job_id', 'unknown')
    created_at = datetime.utcnow().isoformat() + 'Z'
    
    # Process each parsed datasource
    analysis: List[Dict[str, Any]] = []
    
    for datasource in parsed_datasources:
        datasource_id = datasource.get('id', '')
        datasource_name = datasource.get('name', 'unnamed_datasource')
        datasource_type = datasource.get('type', 'unknown')
        connection = datasource.get('connection', {})
        existing_complexity = datasource.get('complexity', 'low')
        
        # Use existing complexity or assess if not available
        if existing_complexity == 'low' and datasource_type != 'unknown':
            complexity = _assess_complexity(datasource_type, connection)
        else:
            complexity = existing_complexity
        
        # Build analysis record
        record = {
            'name': datasource_name,
            'id': datasource_id,
            'type': datasource_type,
            'complexity': complexity,
            'job_id': job_id,
            'created_at': created_at
        }
        
        analysis.append(record)
    
    logger.info(f"Analyzed {len(analysis)} datasources")
    logger.info(f"Types: {', '.join(set(a.get('type', 'unknown') for a in analysis))}")
    
    # Write to BigQuery (temporarily disabled)
    if analysis:
        bigquery_service.insert_rows("datasources", analysis)
    
    # Write to JSON file
    output_dir = state.get('output_dir')
    if output_dir and analysis:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "datasource_analysis.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"Written {len(analysis)} datasource analysis records to {output_file}")
    
    # Update state (only return fields we're modifying to avoid parallel update conflicts)
    logger.info("Completed datasource agent")
    return {
        'datasource_analysis': analysis
    }
