"""File Analysis Agent - Step 0: Extract first-level XML elements and save to separate files."""
import os
from typing import Dict, Any, List
from models.state import AssessmentState
from utils.xml_utils import get_first_level_elements, read_xml_element, split_xml_file_recursive
from utils.logger import logger
from config.settings import get_settings


async def file_analysis_agent(state: AssessmentState) -> AssessmentState:
    """
    File Analysis Agent - Extract first-level XML elements and save to separate files.
    
    INPUT: state with source_files (local paths) and platform
    OUTPUT: state with parsed_elements_paths and output_dir populated
    
    Process:
    1. Get first-level elements using get_first_level_elements() tool
    2. For each element:
       - Read ALL content using read_xml_element() (gets all instances of that element type)
       - Save to output/{job_id}/{element_name}.xml (one file per element type)
       - Store file path and metadata in state
    3. Output: parsed_elements_paths list with all saved files
    """
    logger.info("Starting file analysis agent")
    
    source_files = state.get('source_files', [])
    if not source_files:
        logger.warning("No source files provided")
        state['parsed_elements_paths'] = []
        state['output_dir'] = None
        state['status'] = 'file_analysis_complete'
        return state
    
    first_file = source_files[0]
    file_path = first_file.get('file_path', '')
    platform = first_file.get('platform', 'tableau').lower()
    job_id = state.get('job_id', 'default_job')
    
    logger.info(f"Analyzing file: {file_path} (platform: {platform})")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        state['parsed_elements_paths'] = []
        state['output_dir'] = None
        state['status'] = 'file_analysis_complete'
        state['errors'] = state.get('errors', []) + [f"File not found: {file_path}"]
        return state
    
    try:
        # Create output directory
        output_dir = os.path.join("output", job_id)
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")
        
        # Get first-level elements
        element_names = get_first_level_elements(file_path)
        if not element_names:
            logger.warning("No first-level elements found")
            state['parsed_elements_paths'] = []
            state['output_dir'] = output_dir
            state['status'] = 'file_analysis_complete'
            return state
        
        logger.info(f"Found {len(element_names)} first-level elements: {element_names}")
        
        # Process each element
        parsed_elements_paths: List[Dict[str, Any]] = []
        settings = get_settings()
        size_threshold = settings.chunk_max_size_bytes
        
        for element_name in element_names:
            logger.info(f"Processing element: {element_name}")
            
            # Read element content (all instances of this element type)
            element_content = read_xml_element(file_path, element_name)
            
            if not element_content:
                logger.warning(f"No content found for element '{element_name}', skipping")
                continue
            
            # Save to file
            element_file_path = os.path.join(output_dir, f"{element_name}.xml")
            with open(element_file_path, 'w', encoding='utf-8') as f:
                f.write(element_content)
            
            initial_file_size = os.path.getsize(element_file_path)
            logger.info(f"Saved {element_name} to {element_file_path} ({initial_file_size:,} bytes)")
            
            # Recursively split if file is larger than threshold
            if initial_file_size > size_threshold:
                logger.info(
                    f"File {element_file_path} ({initial_file_size:,} bytes) exceeds threshold "
                    f"({size_threshold:,} bytes). Starting recursive splitting..."
                )
                
                split_files = split_xml_file_recursive(
                    element_file_path,
                    output_dir,
                    size_threshold=size_threshold
                )
                
                if split_files:
                    logger.info(
                        f"Split {element_name} into {len(split_files)} files "
                        f"(all ≤ {size_threshold:,} bytes)"
                    )
                    parsed_elements_paths.extend(split_files)
                else:
                    # If splitting failed, keep original file
                    logger.warning(f"Splitting failed for {element_file_path}, keeping original file")
                    parsed_elements_paths.append({
                        'file_path': element_file_path,
                        'size_bytes': initial_file_size
                    })
            else:
                # File is small enough, keep as-is
                parsed_elements_paths.append({
                    'file_path': element_file_path,
                    'size_bytes': initial_file_size
                })
        
        # Update state
        state['parsed_elements_paths'] = parsed_elements_paths
        state['output_dir'] = output_dir
        state['status'] = 'file_analysis_complete'
        
        logger.info(f"Completed file analysis agent - extracted {len(parsed_elements_paths)} elements")
        return state
        
    except Exception as e:
        logger.error(f"Error in file analysis: {e}", exc_info=True)
        state['parsed_elements_paths'] = []
        state['output_dir'] = None
        state['status'] = 'file_analysis_complete'
        state['errors'] = state.get('errors', []) + [f"File analysis error: {str(e)}"]
        return state

