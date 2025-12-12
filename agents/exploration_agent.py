"""Exploration Agent - Step 1: Discover components from parsed element files."""
import os
import json
from typing import Dict, Any
from models.state import AssessmentState
from services.llm_service import llm_service
from config.settings import get_settings
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
    
    # Get size threshold from settings
    settings = get_settings()
    size_threshold = settings.chunk_max_size_bytes  # Default: 500KB
    
    try:
        # Load element files into memory (only files ≤ 500KB)
        element_contents: Dict[str, str] = {}
        skipped_files = []
        
        for element_info in parsed_elements_paths:
            element_name = element_info.get('element_name')
            element_file_path = element_info.get('file_path')
            size_bytes = element_info.get('size_bytes', 0)
            
            if not element_name or not element_file_path:
                logger.warning(f"Invalid element info: {element_info}, skipping")
                continue
            
            if not os.path.exists(element_file_path):
                logger.warning(f"Element file not found: {element_file_path}, skipping")
                continue
            
            # Check file size - skip files > 500KB
            if size_bytes > size_threshold:
                warning_msg = f"Skipping {element_name} ({size_bytes:,} bytes) - exceeds {size_threshold:,} bytes limit. Will handle with file splitting later."
                logger.warning(warning_msg)
                skipped_files.append({
                    'element_name': element_name,
                    'size_bytes': size_bytes,
                    'reason': 'exceeds_size_limit'
                })
                continue
            
            # Read element file content (only for files ≤ 500KB)
            with open(element_file_path, 'r', encoding='utf-8') as f:
                element_content = f.read()
            
            element_contents[element_name] = element_content
            logger.info(f"Loaded {element_name} ({len(element_content):,} chars, {size_bytes:,} bytes)")
        
        # Log skipped files summary
        if skipped_files:
            logger.warning(f"Skipped {len(skipped_files)} large files: {[f['element_name'] for f in skipped_files]}")
        
        if not element_contents:
            if skipped_files:
                logger.warning("No element contents loaded - all files exceeded size limit")
            else:
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
        
        # Write discovered components to JSON file
        if output_dir and discovered_components:
            os.makedirs(output_dir, exist_ok=True)
            components_file = os.path.join(output_dir, "discovered_components.json")
            with open(components_file, 'w', encoding='utf-8') as f:
                json.dump(discovered_components, f, indent=2)
            logger.info(f"Written discovered components to {components_file}")
        
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
