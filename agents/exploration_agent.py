"""Exploration Agent - Step 1: Discover components from parsed element files."""
import os
import json
from typing import Dict, Any, List
from datetime import datetime
from models.state import AssessmentState
from services.llm_service import llm_service
from config.settings import get_settings
from utils.logger import logger


def load_feature_catalog(platform: str) -> Dict[str, Any]:
    """
    Load feature catalog for the given platform.
    
    Args:
        platform: BI platform name (tableau, cognos, microstrategy, power_bi)
    
    Returns:
        Feature catalog dict for the platform, or empty dict if not found
    """
    try:
        catalog_path = os.path.join("config", "feature_catalog.json")
        if not os.path.exists(catalog_path):
            logger.warning(f"Feature catalog not found: {catalog_path}")
            return {}
        
        with open(catalog_path, 'r', encoding='utf-8') as f:
            full_catalog = json.load(f)
        
        platform_catalog = full_catalog.get(platform, {})
        if not platform_catalog:
            logger.warning(f"No feature catalog found for platform: {platform}")
            return {}
        
        logger.info(f"Loaded feature catalog for platform: {platform}")
        return platform_catalog
        
    except Exception as e:
        logger.error(f"Error loading feature catalog: {e}", exc_info=True)
        return {}


def merge_discoveries(all_discoveries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge discoveries from multiple files by component type.
    
    Args:
        all_discoveries: List of discovery results from each file
    
    Returns:
        Merged catalog with all components organized by type
    """
    merged = {
        "dashboards": [],
        "worksheets": [],
        "datasources": [],
        "calculations": [],
        "filters": [],
        "parameters": []
    }
    
    for discovery in all_discoveries:
        components = discovery.get("components", {})
        for component_type in merged.keys():
            if component_type in components and isinstance(components[component_type], list):
                merged[component_type].extend(components[component_type])
    
    return merged


def build_relationships(merged_catalog: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Build relationships between components from the merged catalog.
    
    Args:
        merged_catalog: Merged component catalog
    
    Returns:
        List of relationship dicts
    """
    relationships = []
    
    # Dashboard → Worksheets
    for dashboard in merged_catalog.get("dashboards", []):
        dashboard_id = dashboard.get("id")
        if not dashboard_id:
            continue
        
        # Check parsing_instructions for worksheets_used
        parsing_instructions = dashboard.get("parsing_instructions", {})
        worksheets_instruction = parsing_instructions.get("worksheets_used", "")
        
        # Try to find worksheet references in dashboard metadata
        # This is a simplified version - actual relationships should be extracted by LLM
        # For now, we'll rely on LLM to include relationships in the discovery result
        
    # Worksheet → Datasources, Calculations, Filters
    for worksheet in merged_catalog.get("worksheets", []):
        worksheet_id = worksheet.get("id")
        if not worksheet_id:
            continue
        
        # Relationships should be discovered by LLM and included in discovery result
        # This function can be enhanced to extract relationships from component metadata
    
    # Calculation → Datasource
    for calculation in merged_catalog.get("calculations", []):
        calc_id = calculation.get("id")
        datasource_id = calculation.get("datasource_id")
        
        if calc_id and datasource_id:
            relationships.append({
                "type": "calculation_belongs_to_datasource",
                "from": calc_id,
                "to": [datasource_id]
            })
    
    return relationships


async def exploration_agent(state: AssessmentState) -> AssessmentState:
    """
    Exploration Agent - Discover components from parsed element files using LLM.
    
    INPUT: state with parsed_elements_paths (from File Analysis Agent)
    OUTPUT: state with discovered_components populated (component catalog with relationships)
    
    Process:
    1. Get all files from parsed_elements_paths (all ≤500KB from File Analysis Agent)
    2. Get platform from state
    3. Load feature catalog from config/feature_catalog.json
    4. For each file: Call LLM to discover components, features, and parsing instructions
    5. Merge results by component type
    6. Build relationships
    7. Create final index/catalog
    """
    
    logger.info("Starting exploration agent")
    
    # 1. Get files and platform
    parsed_elements_paths = state.get('parsed_elements_paths', [])
    output_dir = state.get('output_dir')
    
    if not parsed_elements_paths:
        logger.warning("No parsed elements found from File Analysis Agent")
        state['discovered_components'] = {}
        state['status'] = 'exploration_complete'
        return state
    
    source_files = state.get('source_files', [])
    if not source_files:
        logger.warning("No source files found")
        state['discovered_components'] = {}
        state['status'] = 'exploration_complete'
        return state
    
    first_file = source_files[0]
    platform = first_file.get('platform', 'tableau').lower()
    
    logger.info(f"Processing {len(parsed_elements_paths)} parsed element files (platform: {platform})")
    
    # 2. Load feature catalog
    feature_catalog = load_feature_catalog(platform)
    if not feature_catalog:
        logger.warning(f"No feature catalog found for {platform}, proceeding without it")
        feature_catalog = {}
    
    # Get size threshold from settings
    settings = get_settings()
    size_threshold = settings.chunk_max_size_bytes  # Default: 500KB
    
    try:
        # 3. Process each file with LLM (one call per file)
        all_discoveries = []
        skipped_files = []
        
        for file_info in parsed_elements_paths:
            file_path = file_info.get('file_path')
            size_bytes = file_info.get('size_bytes', 0)
            
            if not file_path:
                logger.warning(f"Invalid file info: {file_info}, skipping")
                continue
            
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}, skipping")
                continue
            
            # Check file size - skip files > threshold
            if size_bytes > size_threshold:
                logger.warning(
                    f"Skipping {file_path} ({size_bytes:,} bytes) - exceeds "
                    f"{size_threshold:,} bytes limit. Should have been split by File Analysis Agent."
                )
                skipped_files.append({
                    'file_path': file_path,
                    'size_bytes': size_bytes,
                    'reason': 'exceeds_size_limit'
                })
                continue
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                continue
            
            if not file_content.strip():
                logger.warning(f"Empty file: {file_path}, skipping")
                continue
            
            # Call LLM to discover components from this file
            logger.info(f"Discovering components from {file_path} ({size_bytes:,} bytes)")
            
            try:
                discovery = await llm_service.discover_components_from_file(
                    file_path=file_path,
                    file_content=file_content,
                    platform=platform,
                    feature_catalog=feature_catalog
                )
                
                if discovery:
                    all_discoveries.append(discovery)
                    components = discovery.get("components", {})
                    total = sum(len(v) if isinstance(v, list) else 0 for v in components.values())
                    logger.info(f"Discovered {total} components from {file_path}")
                else:
                    logger.warning(f"No components discovered from {file_path}")
                    
            except Exception as e:
                logger.error(f"Error discovering components from {file_path}: {e}", exc_info=True)
                # Continue with other files even if one fails
                continue
        
        # Log skipped files summary
        if skipped_files:
            logger.warning(f"Skipped {len(skipped_files)} large files")
        
        if not all_discoveries:
            logger.warning("No discoveries made from any files")
            state['discovered_components'] = {}
            state['status'] = 'exploration_complete'
            return state
        
        # 4. Merge discoveries by component type
        merged_catalog = merge_discoveries(all_discoveries)
        
        # 5. Build relationships (also collect from discovery results)
        relationships = build_relationships(merged_catalog)
        
        # Also collect relationships from individual discovery results
        for discovery in all_discoveries:
            discovery_relationships = discovery.get("relationships", [])
            if discovery_relationships:
                relationships.extend(discovery_relationships)
        
        # 6. Collect new features discovered
        new_features = {}
        try:
            for discovery in all_discoveries:
                new_features_list = discovery.get("new_features_discovered", [])
                if new_features_list:
                    # Merge new features by component type
                    # Handle both dict format and string format
                    for feature_info in new_features_list:
                        try:
                            if isinstance(feature_info, dict):
                                comp_type = feature_info.get("component_type")
                                feature_name = feature_info.get("feature_name")
                                if comp_type and feature_name:
                                    if comp_type not in new_features:
                                        new_features[comp_type] = []
                                    if feature_name not in new_features[comp_type]:
                                        new_features[comp_type].append(feature_name)
                            elif isinstance(feature_info, str):
                                # If it's just a string, log it but can't categorize by component type
                                logger.debug(f"New feature discovered (string format, skipping): {feature_info}")
                                # Skip string-only features as we need component type for categorization
                            else:
                                logger.warning(f"Unexpected feature_info format: {type(feature_info)}, value: {feature_info}")
                        except Exception as e:
                            logger.warning(f"Error processing feature_info: {e}, feature_info: {feature_info}")
                            continue
        except Exception as e:
            logger.error(f"Error collecting new features: {e}", exc_info=True)
            # Continue with empty new_features dict - don't fail entire agent
        
        # 7. Create final index
        component_index = {
            "platform": platform,
            "discovery_metadata": {
                "total_files_processed": len(all_discoveries),
                "total_files_skipped": len(skipped_files),
                "discovery_timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "components": merged_catalog,
            "feature_catalog": {
                comp_type: {
                    "standard_features": catalog.get("standard_features", []),
                    "new_features_discovered": new_features.get(comp_type, [])
                }
                for comp_type, catalog in feature_catalog.items()
            },
            "relationships": relationships
        }
        
        # Log summary
        logger.info(f"Discovery complete:")
        logger.info(f"  - Dashboards: {len(merged_catalog.get('dashboards', []))}")
        logger.info(f"  - Worksheets: {len(merged_catalog.get('worksheets', []))}")
        logger.info(f"  - Datasources: {len(merged_catalog.get('datasources', []))}")
        logger.info(f"  - Calculations: {len(merged_catalog.get('calculations', []))}")
        logger.info(f"  - Filters: {len(merged_catalog.get('filters', []))}")
        logger.info(f"  - Parameters: {len(merged_catalog.get('parameters', []))}")
        logger.info(f"  - Relationships: {len(relationships)}")
        
        # 8. Save to JSON file
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            components_file = os.path.join(output_dir, "discovered_components.json")
            with open(components_file, 'w', encoding='utf-8') as f:
                json.dump(component_index, f, indent=2)
            logger.info(f"Written discovered components to {components_file}")
        
        # 9. Update state
        state['discovered_components'] = component_index
        state['status'] = 'exploration_complete'
        
        logger.info("Completed exploration agent")
        return state
        
    except Exception as e:
        logger.error(f"Error in exploration agent: {e}", exc_info=True)
        state['discovered_components'] = {}
        state['status'] = 'exploration_complete'
        state['errors'] = state.get('errors', []) + [f"Exploration error: {str(e)}"]
        return state
