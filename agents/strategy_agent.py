"""Strategy Agent - Step 4: Make recommendations."""
from typing import Dict, Any, List
from models.state import AssessmentState
from services.llm_service import llm_service
from services.bigquery_service import bigquery_service
from dummy_data.sample_data import DUMMY_STRATEGY
from utils.logger import logger


async def strategy_agent(state: AssessmentState) -> AssessmentState:
    """
    Strategy Agent - Generate migration recommendations and strategy.
    
    INPUT: All analyses from Step 3 (read from BigQuery or state)
    OUTPUT: state with final_report populated
    WRITES: None
    
    FUTURE LLM IMPLEMENTATION:
    Currently uses dummy data. To implement with real LLM:
    1. Remove DUMMY_STRATEGY usage
    2. Collect all analyses from state or read from BigQuery
    3. Call llm_service.generate_recommendations(analyses)
    4. Parse LLM response into structured format
    """
    
    logger.info("Starting strategy agent")
    
    job_id = state.get('job_id', 'unknown')
    
    # Step 1: Collect all analyses
    # FUTURE: Optionally read from BigQuery instead of state
    # calculation_analysis = bigquery_service.read_rows("calculations_analysis", job_id)
    # visualization_analysis = bigquery_service.read_rows("visualizations_analysis", job_id)
    # dashboard_analysis = bigquery_service.read_rows("dashboards_analysis", job_id)
    # datasource_analysis = bigquery_service.read_rows("datasources_analysis", job_id)
    
    analyses = {
        "calculations": state.get('calculation_analysis', []),
        "visualizations": state.get('visualization_analysis', []),
        "dashboards": state.get('dashboard_analysis', []),
        "datasources": state.get('datasource_analysis', []),
    }
    
    total_components = sum(len(analysis) for analysis in analyses.values())
    logger.info(f"Generating recommendations from {total_components} analyzed components")
    
    # Step 2: Get recommendations (from LLM service)
    # FUTURE: Call LLM to generate recommendations
    # final_report = await llm_service.generate_recommendations(analyses)
    
    # Currently using dummy data
    final_report = DUMMY_STRATEGY.copy()
    
    logger.info(f"Generated final report with {len(final_report.get('migration_recommendations', []))} recommendations")
    logger.info(f"Estimated total effort: {final_report.get('final_estimated_effort_hours', 0)} hours")
    
    # Step 3: Update state
    state['final_report'] = final_report
    state['status'] = 'strategy_complete'
    
    logger.info("Completed strategy agent")
    return state

