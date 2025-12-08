"""Exploration Agent - Step 1: Discover components from metadata."""
import os
from typing import Dict, Any, List
from models.state import AssessmentState
from services.llm_service import llm_service
from utils.xml_utils import read_xml_section
from utils.logger import logger


async def exploration_agent(state: AssessmentState) -> AssessmentState:
    """
    Exploration Agent - Discover components from local metadata files.
    
    INPUT: state with source_files (local paths) and platform
    OUTPUT: state with discovered_components populated
    
    Process:
    1. Read XML file from local path
    2. Call Gemini to discover components
    3. Parse and return discovered components
    """
    
    logger.info("Starting exploration agent")
    
    source_files = state.get('source_files', [])
    if not source_files:
        logger.warning("No source files provided")
        state['discovered_components'] = {
            "dashboards": [],
            "metrics": [],
            "visualizations": [],
            "datasources": []
        }
        state['status'] = 'exploration_complete'
        return state
    
    # Process one file at a time (first file for now)
    first_file = source_files[0]
    file_path = first_file.get('file_path', '')
    platform = first_file.get('platform', 'tableau')  # Default to tableau
    
    logger.info(f"Processing file: {file_path} (platform: {platform})")
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        state['discovered_components'] = {
            "dashboards": [],
            "metrics": [],
            "visualizations": [],
            "datasources": []
        }
        state['status'] = 'exploration_complete'
        return state
    
    # Check for file analysis strategy
    strategy = state.get('file_analysis_strategy')
    
    try:
        if strategy and strategy.get('chunks'):
            # Use strategy-based chunk processing
            logger.info(f"Using file analysis strategy with {len(strategy['chunks'])} chunks")
            discovered_components = await _process_with_strategy(
                file_path, platform, strategy
            )
        else:
            # Fallback to current behavior (read full file)
            logger.info("No strategy found, using full file processing")
            discovered_components = await _process_full_file(file_path, platform)
        
        # Log discovered components
        dashboards = discovered_components.get('dashboards', [])
        metrics = discovered_components.get('metrics', [])
        visualizations = discovered_components.get('visualizations', [])
        datasources = discovered_components.get('datasources', [])
        
        logger.info(f"Discovered {len(dashboards)} dashboards")
        logger.info(f"Discovered {len(metrics)} metrics")
        logger.info(f"Discovered {len(visualizations)} visualizations")
        logger.info(f"Discovered {len(datasources)} datasources")
        
        # Update state
        state['discovered_components'] = discovered_components
        state['status'] = 'exploration_complete'
        
        logger.info("Completed exploration agent")
        return state
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        state['discovered_components'] = {
            "dashboards": [],
            "metrics": [],
            "visualizations": [],
            "datasources": []
        }
        state['status'] = 'exploration_complete'
        state['errors'] = state.get('errors', []) + [f"Exploration error: {str(e)}"]
        return state


async def _process_with_strategy(
    file_path: str,
    platform: str,
    strategy: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process file in chunks according to strategy.
    
    Args:
        file_path: Path to the file
        platform: BI platform name
        strategy: Splitting strategy from file analysis agent
        
    Returns:
        Merged discovered components from all chunks
    """
    all_components = {
        "dashboards": [],
        "metrics": [],
        "visualizations": [],
        "datasources": []
    }
    
    # Get processing order
    processing_order = strategy.get('processing_order', [])
    chunks = {chunk['chunk_id']: chunk for chunk in strategy.get('chunks', [])}
    
    # Track context from previous chunks
    context_cache = {}
    
    for chunk_id in processing_order:
        chunk = chunks.get(chunk_id)
        if not chunk:
            logger.warning(f"Chunk {chunk_id} not found in strategy")
            continue
        
        logger.info(f"Processing chunk: {chunk_id} - {chunk.get('target_elements', [])}")
        
        # Get target elements and context needed
        target_elements = chunk.get('target_elements', [])
        context_needed = chunk.get('context_needed', [])
        
        # Read XML section for this chunk
        try:
            chunk_content = read_xml_section(
                file_path,
                target_elements,
                context_needed
            )
            
            if not chunk_content:
                logger.warning(f"No content extracted for chunk {chunk_id}")
                continue
            
            logger.info(f"Extracted {len(chunk_content)} characters for chunk {chunk_id}")
            
            # Call Gemini to discover components in this chunk
            chunk_components = await llm_service.analyze_components(
                file_content=chunk_content,
                platform=platform,
                file_path=file_path
            )
            
            # Merge results
            _merge_components(all_components, chunk_components)
            
            # Store context for future chunks
            if context_needed:
                context_cache[chunk_id] = chunk_components
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_id}: {e}")
            continue
    
    return all_components


async def _process_full_file(file_path: str, platform: str) -> Dict[str, Any]:
    """
    Process full file (fallback when no strategy available).
    
    Args:
        file_path: Path to the file
        platform: BI platform name
        
    Returns:
        Discovered components
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
    
    logger.info(f"Read file: {len(file_content)} characters")
    
    # Call Gemini to discover components
    discovered_components = await llm_service.analyze_components(
        file_content=file_content,
        platform=platform,
        file_path=file_path
    )
    
    return discovered_components


def _merge_components(
    all_components: Dict[str, List[Dict[str, Any]]],
    chunk_components: Dict[str, List[Dict[str, Any]]]
) -> None:
    """
    Merge components from a chunk into the overall results.
    Avoids duplicates by checking component IDs.
    
    Args:
        all_components: Accumulated components (modified in place)
        chunk_components: Components from current chunk
    """
    for component_type in ['dashboards', 'metrics', 'visualizations', 'datasources']:
        chunk_items = chunk_components.get(component_type, [])
        existing_ids = {item.get('id') for item in all_components.get(component_type, [])}
        
        for item in chunk_items:
            item_id = item.get('id')
            if item_id and item_id not in existing_ids:
                all_components[component_type].append(item)
                existing_ids.add(item_id)
            elif not item_id:
                # If no ID, add anyway (might be duplicate but we can't tell)
                all_components[component_type].append(item)
