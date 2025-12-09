"""Exploration Agent - Step 1: Discover components from metadata."""
import os
from typing import Dict, Any
from models.state import AssessmentState
from services.llm_service import llm_service
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
            # Use agent-driven approach: give strategy to Gemini
            logger.info(f"Using file analysis strategy with {len(strategy['chunks'])} chunks")
            
            # Check chunk sizes BEFORE calling Gemini (prevent context window errors)
            processing_order = strategy.get('processing_order', [])
            chunks = {chunk['chunk_id']: chunk for chunk in strategy.get('chunks', [])}
            chunk_issues = []
            
            from utils.xml_utils import read_xml_element
            
            for chunk_id in processing_order:
                chunk = chunks.get(chunk_id)
                if not chunk:
                    continue
                
                # Read chunk to check size
                target_elements = chunk.get('target_elements', [])
                chunk_content_parts = []
                
                for element_name in target_elements:
                    element_content = read_xml_element(file_path, element_name)
                    if element_content:
                        chunk_content_parts.append(element_content)
                
                if chunk_content_parts:
                    chunk_content = '\n\n'.join(chunk_content_parts)
                    chunk_size = len(chunk_content)
                    from config.settings import get_settings
                    settings = get_settings()
                    max_size = chunk.get('max_size_bytes', settings.chunk_max_size_bytes)
                    
                    if chunk_size > max_size:
                        chunk_issues.append({
                            'chunk_id': chunk_id,
                            'actual_size': chunk_size,
                            'max_size': max_size,
                            'target_elements': target_elements
                        })
            
            if chunk_issues:
                logger.warning(f"Chunks exceed size limits, triggering strategy refinement")
                logger.warning(f"Problematic chunks: {[c['chunk_id'] for c in chunk_issues]}")
                
                refinement_count = state.get('strategy_refinement_count', 0)
                if refinement_count >= 3:
                    logger.error("Max refinement attempts (3) reached, cannot refine further")
                    state['errors'] = state.get('errors', []) + [
                        "Strategy refinement failed after 3 attempts - chunks too large"
                    ]
                    state['discovered_components'] = {
                        "dashboards": [],
                        "metrics": [],
                        "visualizations": [],
                        "datasources": []
                    }
                    state['status'] = 'exploration_complete'
                    return state
                
                state['strategy_refinement_needed'] = {
                    'reason': 'chunks_too_large',
                    'problematic_chunks': chunk_issues
                }
                state['discovered_components'] = {
                    "dashboards": [],
                    "metrics": [],
                    "visualizations": [],
                    "datasources": []
                }
                state['status'] = 'strategy_refinement_needed'
                return state  # Loop back to file_analysis
            
            # Try to process with strategy
            try:
                discovered_components = await llm_service.analyze_components_with_strategy(
                    strategy=strategy,
                    file_path=file_path,
                    platform=platform
                )
            except Exception as e:
                error_str = str(e).lower()
                error_type = type(e).__name__
                
                # Check if it's a context window error
                if 'token' in error_str or 'context' in error_str or 'limit' in error_str:
                    logger.error("Context window error detected, triggering strategy refinement")
                    
                    refinement_count = state.get('strategy_refinement_count', 0)
                    if refinement_count >= 3:
                        logger.error("Max refinement attempts (3) reached, cannot refine further")
                        state['errors'] = state.get('errors', []) + [
                            f"Strategy refinement failed after 3 attempts - context window error: {error_type}"
                        ]
                        state['discovered_components'] = {
                            "dashboards": [],
                            "metrics": [],
                            "visualizations": [],
                            "datasources": []
                        }
                        state['status'] = 'exploration_complete'
                        return state
                    
                    state['strategy_refinement_needed'] = {
                        'reason': 'context_window_exceeded',
                        'error': str(e),
                        'error_type': error_type
                    }
                    state['discovered_components'] = {
                        "dashboards": [],
                        "metrics": [],
                        "visualizations": [],
                        "datasources": []
                    }
                    state['status'] = 'strategy_refinement_needed'
                    return state  # Loop back to file_analysis
                else:
                    # Other errors - log and re-raise
                    logger.error(f"Error analyzing components with strategy: {e}", exc_info=True)
                    raise
            
            # Check if all components are empty
            dashboards = discovered_components.get('dashboards', [])
            metrics = discovered_components.get('metrics', [])
            visualizations = discovered_components.get('visualizations', [])
            datasources = discovered_components.get('datasources', [])
            total = len(dashboards) + len(metrics) + len(visualizations) + len(datasources)
            
            if total == 0:
                logger.warning("All components empty, triggering strategy refinement")
                
                refinement_count = state.get('strategy_refinement_count', 0)
                if refinement_count >= 3:
                    logger.error("Max refinement attempts (3) reached, cannot refine further")
                    state['errors'] = state.get('errors', []) + [
                        "Strategy refinement failed after 3 attempts - empty components"
                    ]
                    state['discovered_components'] = discovered_components
                    state['status'] = 'exploration_complete'
                    return state
                
                state['strategy_refinement_needed'] = {
                    'reason': 'empty_components',
                    'possible_causes': ['wrong_element_names', 'context_window_exceeded', 'parsing_failed']
                }
                state['discovered_components'] = discovered_components  # Set empty result
                state['status'] = 'strategy_refinement_needed'
                return state  # Loop back to file_analysis
            
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
        logger.error(f"Error processing file: {e}", exc_info=True)
        state['discovered_components'] = {
            "dashboards": [],
            "metrics": [],
            "visualizations": [],
            "datasources": []
        }
        state['status'] = 'exploration_complete'
        state['errors'] = state.get('errors', []) + [f"Exploration error: {str(e)}"]
        return state


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

