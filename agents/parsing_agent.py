"""Parsing Agent - Step 2: Extract complexity-relevant details."""
from typing import Dict, Any
from models.state import AssessmentState
from services.llm_service import llm_service
from dummy_data.sample_data import DUMMY_PARSING
from utils.logger import logger


async def parsing_agent(state: AssessmentState) -> AssessmentState:
    """
    Parsing Agent - Extract complexity-relevant details from components.
    
    INPUT: state with discovered_components
    OUTPUT: state with parsed_metrics, parsed_dashboards, parsed_visualizations, parsed_datasources
    WRITES: None
    
    FUTURE LLM IMPLEMENTATION:
    Currently uses dummy data. To implement with real LLM:
    1. Remove DUMMY_PARSING usage
    2. Call llm_service.extract_complexity_details(state['discovered_components'])
    3. Parse LLM response into structured format
    """
    
    logger.info("Starting parsing agent")
    
    discovered_components = state.get('discovered_components', {})
    if not discovered_components:
        logger.warning("No discovered components found, skipping parsing")
        state['status'] = 'parsing_complete'
        return state
    
    # Step 1: Get data (from state or call LLM service)
    # FUTURE: Call LLM to extract complexity details
    # parsed_data = await llm_service.extract_complexity_details(discovered_components)
    
    # Currently using dummy data
    parsed_data = DUMMY_PARSING
    
    logger.info(f"Parsed {len(parsed_data.get('metrics', []))} metrics")
    logger.info(f"Parsed {len(parsed_data.get('dashboards', []))} dashboards")
    logger.info(f"Parsed {len(parsed_data.get('visualizations', []))} visualizations")
    logger.info(f"Parsed {len(parsed_data.get('datasources', []))} datasources")
    
    # Step 2: Update state
    state['parsed_metrics'] = parsed_data.get('metrics', [])
    state['parsed_dashboards'] = parsed_data.get('dashboards', [])
    state['parsed_visualizations'] = parsed_data.get('visualizations', [])
    state['parsed_datasources'] = parsed_data.get('datasources', [])
    state['status'] = 'parsing_complete'
    
    logger.info("Completed parsing agent")
    return state

