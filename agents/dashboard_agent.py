"""Dashboard Agent - Step 3c: Analyze dashboards."""
from typing import List, Dict, Any
from models.state import AssessmentState
from services.llm_service import llm_service
from services.bigquery_service import bigquery_service
from dummy_data.sample_data import DUMMY_DASHBOARD
from utils.logger import logger


async def dashboard_agent(state: AssessmentState) -> AssessmentState:
    """
    Dashboard Agent - Analyze dashboard structure and complexity.
    
    INPUT: state with parsed_dashboards
    OUTPUT: state with dashboard_analysis populated
    WRITES: BigQuery table "dashboards_analysis"
    
    FUTURE LLM IMPLEMENTATION:
    Currently uses dummy data. To implement with real LLM:
    1. Remove DUMMY_DASHBOARD usage
    2. Call llm_service.analyze_dashboards(state['parsed_dashboards'])
    3. Parse LLM response into structured format
    """
    
    logger.info("Starting dashboard agent")
    
    parsed_dashboards = state.get('parsed_dashboards', [])
    if not parsed_dashboards:
        logger.warning("No parsed dashboards found, skipping dashboard analysis")
        state['dashboard_analysis'] = []
        state['status'] = 'analysis_complete'
        return state
    
    # Step 1: Get data (from state or call LLM service)
    # FUTURE: Call LLM to analyze dashboards
    # analysis = await llm_service.analyze_dashboards(parsed_dashboards)
    
    # Currently using dummy data
    analysis = DUMMY_DASHBOARD
    
    # Add job_id to each analysis record
    job_id = state.get('job_id', 'unknown')
    for record in analysis:
        record['job_id'] = job_id
    
    logger.info(f"Analyzed {len(analysis)} dashboards")
    total_worksheets = sum(a.get('worksheets_count', 0) for a in analysis)
    total_filters = sum(a.get('filters_count', 0) for a in analysis)
    logger.info(f"Total worksheets: {total_worksheets}, Total filters: {total_filters}")
    
    # Step 2: Write to BigQuery
    bigquery_service.insert_rows("dashboards_analysis", analysis)
    
    # Step 3: Update state
    state['dashboard_analysis'] = analysis
    state['status'] = 'analysis_complete'
    
    logger.info("Completed dashboard agent")
    return state

