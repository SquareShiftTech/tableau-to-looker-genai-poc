"""Exploration Agent - Step 1: Discover components from parsed element files."""
import os
from typing import Dict, Any
from models.state import AssessmentState
from services.llm_service import llm_service
from utils.logger import logger


async def exploration_agent(state: AssessmentState) -> AssessmentState:
    """
    Exploration Agent - Read parsed element files and extract component catalog.
    
    INPUT: state with parsed_elements_paths (from File Analysis Agent)
    OUTPUT: state with discovered_components populated (component catalog with relationships)
    
    Process:
    1. Read parsed_elements_paths from state
    2. Load all element files into memory (read XML content)
    3. Call llm_service.extract_component_catalog() with element contents
    4. Store component catalog in discovered_components
    """
    
    logger.info("Starting exploration agent")
    
    # Get parsed element files from File Analysis Agent
    parsed_elements_paths = state.get('parsed_elements_paths')
    output_dir = state.get('output_dir')
    
    if not parsed_elements_paths:
        logger.warning("No parsed elements found from File Analysis Agent")
        state['discovered_components'] = {}
        state['status'] = 'exploration_complete'
        return state
    
    # Get platform from source files
    source_files = state.get('source_files', [])
    if not source_files:
        logger.warning("No source files found")
        state['discovered_components'] = {}
        state['status'] = 'exploration_complete'
        return state
    
    first_file = source_files[0]
    platform = first_file.get('platform', 'tableau').lower()
    
    logger.info(f"Processing {len(parsed_elements_paths)} parsed element files (platform: {platform})")
    
    try:
        # Load all element files into memory
        element_contents: Dict[str, str] = {}
        
        for element_info in parsed_elements_paths:
            element_name = element_info.get('element_name')
            element_file_path = element_info.get('file_path')
            
            if not element_name or not element_file_path:
                logger.warning(f"Invalid element info: {element_info}, skipping")
                continue
            
            if not os.path.exists(element_file_path):
                logger.warning(f"Element file not found: {element_file_path}, skipping")
                continue
            
            # Read element file content
            with open(element_file_path, 'r', encoding='utf-8') as f:
                element_content = f.read()
            
            element_contents[element_name] = element_content
            logger.info(f"Loaded {element_name} ({len(element_content):,} chars)")
        
        if not element_contents:
            logger.warning("No element contents loaded")
            state['discovered_components'] = {}
            state['status'] = 'exploration_complete'
            return state
        
        # Call LLM to extract component catalog
        logger.info(f"Extracting component catalog from {len(element_contents)} elements")
        discovered_components = await llm_service.extract_component_catalog(
            element_contents=element_contents,
            platform=platform,
            output_dir=output_dir or "output"
        )
        
        # Log discovered components
        dashboards = discovered_components.get('dashboards', [])
        worksheets = discovered_components.get('worksheets', [])
        datasources = discovered_components.get('datasources', [])
        filters = discovered_components.get('filters', [])
        parameters = discovered_components.get('parameters', [])
        calculations = discovered_components.get('calculations', [])
        
        logger.info(f"Discovered {len(dashboards)} dashboards")
        logger.info(f"Discovered {len(worksheets)} worksheets")
        logger.info(f"Discovered {len(datasources)} datasources")
        logger.info(f"Discovered {len(filters)} filters")
        logger.info(f"Discovered {len(parameters)} parameters")
        logger.info(f"Discovered {len(calculations)} calculations")
        
        # Update state
        state['discovered_components'] = discovered_components
        state['status'] = 'exploration_complete'
        
        logger.info("Completed exploration agent")
        return state
        
    except Exception as e:
        logger.error(f"Error in exploration agent: {e}", exc_info=True)
        state['discovered_components'] = {}
        state['status'] = 'exploration_complete'
        state['errors'] = state.get('errors', []) + [f"Exploration error: {str(e)}"]
        return state
