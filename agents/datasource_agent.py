"""Data Source Agent - Step 3d: Analyze data sources."""
from typing import List, Dict, Any
from models.state import AssessmentState
from services.llm_service import llm_service
from services.bigquery_service import bigquery_service
from dummy_data.sample_data import DUMMY_DATASOURCE
from utils.logger import logger


async def datasource_agent(state: AssessmentState) -> AssessmentState:
    """
    Data Source Agent - Analyze data source compatibility and complexity.
    
    INPUT: state with parsed_datasources
    OUTPUT: state with datasource_analysis populated
    WRITES: BigQuery table "datasources_analysis"
    
    FUTURE LLM IMPLEMENTATION:
    Currently uses dummy data. To implement with real LLM:
    1. Remove DUMMY_DATASOURCE usage
    2. Call llm_service.analyze_datasources(state['parsed_datasources'])
    3. Parse LLM response into structured format
    """
    
    logger.info("Starting datasource agent")
    
    parsed_datasources = state.get('parsed_datasources', [])
    if not parsed_datasources:
        logger.warning("No parsed datasources found, skipping datasource analysis")
        state['datasource_analysis'] = []
        state['status'] = 'analysis_complete'
        return state
    
    # Step 1: Get data (from state or call LLM service)
    # FUTURE: Call LLM to analyze datasources
    # analysis = await llm_service.analyze_datasources(parsed_datasources)
    
    # Currently using dummy data
    analysis = DUMMY_DATASOURCE
    
    # Add job_id to each analysis record
    job_id = state.get('job_id', 'unknown')
    for record in analysis:
        record['job_id'] = job_id
    
    logger.info(f"Analyzed {len(analysis)} datasources")
    logger.info(f"Compatibility: {', '.join(set(a.get('compatibility_level', 'unknown') for a in analysis))}")
    
    # Step 2: Write to BigQuery
    bigquery_service.insert_rows("datasources_analysis", analysis)
    
    # Step 3: Update state
    state['datasource_analysis'] = analysis
    state['status'] = 'analysis_complete'
    
    logger.info("Completed datasource agent")
    return state

