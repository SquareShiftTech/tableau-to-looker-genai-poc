"""Visualization Agent - Step 3b: Analyze visualizations."""
from typing import List, Dict, Any
from models.state import AssessmentState
from services.llm_service import llm_service
from services.bigquery_service import bigquery_service
from dummy_data.sample_data import DUMMY_VISUALIZATION
from utils.logger import logger


async def visualization_agent(state: AssessmentState) -> AssessmentState:
    """
    Visualization Agent - Analyze visualization complexity.
    
    INPUT: state with parsed_visualizations
    OUTPUT: state with visualization_analysis populated
    WRITES: BigQuery table "visualizations_analysis"
    
    FUTURE LLM IMPLEMENTATION:
    Currently uses dummy data. To implement with real LLM:
    1. Remove DUMMY_VISUALIZATION usage
    2. Call llm_service.analyze_visualizations(state['parsed_visualizations'])
    3. Parse LLM response into structured format
    """
    
    logger.info("Starting visualization agent")
    
    parsed_visualizations = state.get('parsed_visualizations', [])
    if not parsed_visualizations:
        logger.warning("No parsed visualizations found, skipping visualization analysis")
        state['visualization_analysis'] = []
        state['status'] = 'analysis_complete'
        return state
    
    # Step 1: Get data (from state or call LLM service)
    # FUTURE: Call LLM to analyze visualizations
    # analysis = await llm_service.analyze_visualizations(parsed_visualizations)
    
    # Currently using dummy data
    analysis = DUMMY_VISUALIZATION
    
    # Add job_id to each analysis record
    job_id = state.get('job_id', 'unknown')
    for record in analysis:
        record['job_id'] = job_id
    
    logger.info(f"Analyzed {len(analysis)} visualizations")
    logger.info(f"Chart types: {', '.join(set(a.get('chart_type', 'unknown') for a in analysis))}")
    
    # Step 2: Write to BigQuery
    bigquery_service.insert_rows("visualizations_analysis", analysis)
    
    # Step 3: Update state
    state['visualization_analysis'] = analysis
    state['status'] = 'analysis_complete'
    
    logger.info("Completed visualization agent")
    return state

