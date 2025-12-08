"""Calculation Agent - Step 3a: Analyze metrics."""
from typing import List, Dict, Any
from models.state import AssessmentState
from services.llm_service import llm_service
from services.bigquery_service import bigquery_service
from dummy_data.sample_data import DUMMY_CALCULATION
from utils.logger import logger


async def calculation_agent(state: AssessmentState) -> AssessmentState:
    """
    Calculation Agent - Analyze metric complexity.
    
    INPUT: state with parsed_metrics
    OUTPUT: state with calculation_analysis populated
    WRITES: BigQuery table "calculations_analysis"
    
    FUTURE LLM IMPLEMENTATION:
    Currently uses dummy data. To implement with real LLM:
    1. Remove DUMMY_CALCULATION usage
    2. Call llm_service.analyze_calculations(state['parsed_metrics'])
    3. Parse LLM response into structured format
    """
    
    logger.info("Starting calculation agent")
    
    parsed_metrics = state.get('parsed_metrics', [])
    if not parsed_metrics:
        logger.warning("No parsed metrics found, skipping calculation analysis")
        state['calculation_analysis'] = []
        state['status'] = 'analysis_complete'
        return state
    
    # Step 1: Get data (from state or call LLM service)
    # FUTURE: Call LLM to analyze calculations
    # analysis = await llm_service.analyze_calculations(parsed_metrics)
    
    # Currently using dummy data
    analysis = DUMMY_CALCULATION
    
    # Add job_id to each analysis record
    job_id = state.get('job_id', 'unknown')
    for record in analysis:
        record['job_id'] = job_id
    
    logger.info(f"Analyzed {len(analysis)} calculations")
    logger.info(f"Complexity breakdown: {sum(1 for a in analysis if a.get('complexity_level') == 'low')} low, "
                f"{sum(1 for a in analysis if a.get('complexity_level') == 'medium')} medium, "
                f"{sum(1 for a in analysis if a.get('complexity_level') == 'high')} high")
    
    # Step 2: Write to BigQuery
    bigquery_service.insert_rows("calculations_analysis", analysis)
    
    # Step 3: Update state
    state['calculation_analysis'] = analysis
    state['status'] = 'analysis_complete'
    
    logger.info("Completed calculation agent")
    return state

