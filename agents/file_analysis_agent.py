"""File Analysis Agent - Step 0: Analyze file structure and create splitting strategy."""
import os
from typing import Dict, Any
from models.state import AssessmentState
from services.file_structure_analyzer import TableauStructureAnalyzer
from services.llm_service import llm_service
from utils.logger import logger


async def file_analysis_agent(state: AssessmentState) -> AssessmentState:
    """
    File Analysis Agent - Analyze file structure and create splitting strategy.
    
    INPUT: state with source_files (local paths) and platform
    OUTPUT: state with file_analysis_strategy populated
    
    Process:
    1. Get platform from state (already provided, no detection needed)
    2. Extract structure using lightweight parser (no full file load)
    3. Call Gemini to create splitting strategy
    4. Store strategy in state
    """
    logger.info("Starting file analysis agent")
    
    source_files = state.get('source_files', [])
    if not source_files:
        logger.warning("No source files provided")
        state['file_analysis_strategy'] = None
        state['status'] = 'file_analysis_complete'
        return state
    
    first_file = source_files[0]
    file_path = first_file.get('file_path', '')
    platform = first_file.get('platform', 'tableau').lower()
    
    logger.info(f"Analyzing file: {file_path} (platform: {platform})")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        state['file_analysis_strategy'] = None
        state['status'] = 'file_analysis_complete'
        state['errors'] = state.get('errors', []) + [f"File not found: {file_path}"]
        return state
    
    try:
        # For now: Tableau only (platform comes from state)
        if platform == 'tableau':
            analyzer = TableauStructureAnalyzer()
        else:
            logger.warning(f"Platform {platform} not yet supported, using Tableau analyzer")
            analyzer = TableauStructureAnalyzer()
        
        # Extract structure (lightweight - no full file load)
        structure_info = analyzer.extract_structure(file_path)
        logger.info(f"Extracted structure: {len(structure_info['element_counts'])} unique element types")
        logger.info(f"Element counts: {structure_info['element_counts']}")
        
        # Call Gemini to create splitting strategy
        strategy = await llm_service.create_file_splitting_strategy(
            structure_info=structure_info,
            platform=platform,
            file_path=file_path
        )
        
        # Store strategy in state
        state['file_analysis_strategy'] = strategy
        state['status'] = 'file_analysis_complete'
        
        logger.info(f"Completed file analysis agent - created strategy with {len(strategy.get('chunks', []))} chunks")
        return state
        
    except Exception as e:
        logger.error(f"Error in file analysis: {e}")
        state['file_analysis_strategy'] = None
        state['status'] = 'file_analysis_complete'
        state['errors'] = state.get('errors', []) + [f"File analysis error: {str(e)}"]
        return state

