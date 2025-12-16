"""Test script for Exploration Agent alone (requires pre-processed files from File Analysis Agent)."""
import asyncio
import json
import os
from agents.exploration_agent import exploration_agent
from models.state import AssessmentState
from utils.logger import logger


async def test_exploration_agent_alone():
    """Test the Exploration Agent with pre-processed files."""
    
    print("\n" + "="*80)
    print("EXPLORATION AGENT - STANDALONE TEST")
    print("="*80)
    
    # First, we need files from File Analysis Agent
    # For this test, we'll use a sample output directory or create one
    # In practice, you would run File Analysis Agent first
    
    # Check if we have an existing output directory with parsed elements
    test_output_dir = "output/test_exploration_alone"
    os.makedirs(test_output_dir, exist_ok=True)
    
    # Check if we need to run file analysis first
    # For this test, let's assume we have files from a previous run
    # Or we can create a minimal test scenario
    
    print("\nThis test requires pre-processed files from File Analysis Agent.")
    print("Options:")
    print("  1. Use existing output directory from a previous File Analysis run")
    print("  2. Run File Analysis Agent first (see test_file_analysis_and_exploration.py)")
    
    # Try to find existing parsed elements
    existing_output_dirs = []
    if os.path.exists("output"):
        for item in os.listdir("output"):
            item_path = os.path.join("output", item)
            if os.path.isdir(item_path):
                # Check if it has XML files (from file analysis)
                xml_files = [f for f in os.listdir(item_path) if f.endswith('.xml')]
                if xml_files:
                    existing_output_dirs.append((item, item_path, len(xml_files)))
    
    if not existing_output_dirs:
        print("\n✗ No existing output directories with parsed files found.")
        print("  Please run File Analysis Agent first, or use test_file_analysis_and_exploration.py")
        return
    
    # Use the most recent output directory
    latest_dir = existing_output_dirs[-1]  # Assuming sorted by creation time
    output_dir = latest_dir[1]
    job_id = latest_dir[0]
    
    print(f"\n✓ Using existing output directory: {output_dir}")
    print(f"  Found {latest_dir[2]} XML files")
    
    # Build parsed_elements_paths from existing files
    parsed_elements_paths = []
    for filename in os.listdir(output_dir):
        if filename.endswith('.xml'):
            file_path = os.path.join(output_dir, filename)
            file_size = os.path.getsize(file_path)
            element_name = os.path.splitext(filename)[0]
            
            parsed_elements_paths.append({
                'file_path': file_path,
                'size_bytes': file_size
            })
            
            print(f"  - {filename}: {file_size:,} bytes")
    
    if not parsed_elements_paths:
        print("\n✗ No XML files found in output directory")
        return
    
    # Create state with parsed elements
    state = AssessmentState(
        job_id=job_id,
        source_files=[
            {"platform": "tableau", "file_path": "input_files/tableau/sales_summary_final.xml"},
        ],
        file_analysis_strategy=None,
        strategy_refinement_needed=None,
        strategy_refinement_count=0,
        parsed_elements_paths=parsed_elements_paths,
        output_dir=output_dir,
        discovered_components=None,
        parsed_metrics=None,
        parsed_dashboards=None,
        parsed_visualizations=None,
        parsed_datasources=None,
        parsed_worksheets=None,
        parsed_calculations=None,
        calculation_analysis=None,
        visualization_analysis=None,
        dashboard_analysis=None,
        datasource_analysis=None,
        final_report=None,
        status="file_analysis_complete",
        errors=[],
    )
    
    print("\n" + "-"*80)
    print("RUNNING EXPLORATION AGENT")
    print("-"*80)
    print(f"Platform: {state['source_files'][0]['platform']}")
    print(f"Files to process: {len(parsed_elements_paths)}")
    print("-"*80)
    
    try:
        result = await exploration_agent(state)
        
        print("\n" + "="*80)
        print("EXPLORATION RESULTS")
        print("="*80)
        
        discovered = result.get('discovered_components', {})
        
        if not discovered:
            print("\n✗ No components discovered")
            if result.get('errors'):
                print(f"  Errors: {result['errors']}")
            return
        
        # Extract components from new structure
        platform = discovered.get('platform', 'unknown')
        discovery_metadata = discovered.get('discovery_metadata', {})
        components = discovered.get('components', {})
        relationships = discovered.get('relationships', [])
        feature_catalog = discovered.get('feature_catalog', {})
        
        print(f"\nPlatform: {platform}")
        print(f"Files Processed: {discovery_metadata.get('total_files_processed', 0)}")
        print(f"Files Skipped: {discovery_metadata.get('total_files_skipped', 0)}")
        print(f"Discovery Timestamp: {discovery_metadata.get('discovery_timestamp', 'N/A')}")
        
        dashboards = components.get('dashboards', [])
        worksheets = components.get('worksheets', [])
        datasources = components.get('datasources', [])
        calculations = components.get('calculations', [])
        filters = components.get('filters', [])
        parameters = components.get('parameters', [])
        
        print("\n" + "-"*80)
        print("COMPONENTS DISCOVERED")
        print("-"*80)
        print(f"Dashboards: {len(dashboards)}")
        for dash in dashboards[:3]:
            print(f"  - {dash.get('name', 'N/A')} (id: {dash.get('id', 'N/A')})")
            print(f"    File: {dash.get('file', 'N/A')}")
            features = dash.get('features_to_extract', [])
            print(f"    Features: {', '.join(features[:3])}{'...' if len(features) > 3 else ''}")
        if len(dashboards) > 3:
            print(f"  ... and {len(dashboards) - 3} more")
        
        print(f"\nWorksheets: {len(worksheets)}")
        for ws in worksheets[:3]:
            print(f"  - {ws.get('name', 'N/A')} (id: {ws.get('id', 'N/A')})")
            print(f"    File: {ws.get('file', 'N/A')}")
            features = ws.get('features_to_extract', [])
            print(f"    Features: {', '.join(features[:3])}{'...' if len(features) > 3 else ''}")
        if len(worksheets) > 3:
            print(f"  ... and {len(worksheets) - 3} more")
        
        print(f"\nDatasources: {len(datasources)}")
        for ds in datasources[:3]:
            print(f"  - {ds.get('name', 'N/A')} (id: {ds.get('id', 'N/A')})")
            print(f"    File: {ds.get('file', 'N/A')}")
        if len(datasources) > 3:
            print(f"  ... and {len(datasources) - 3} more")
        
        print(f"\nCalculations: {len(calculations)}")
        print(f"Filters: {len(filters)}")
        print(f"Parameters: {len(parameters)}")
        
        print("\n" + "-"*80)
        print("RELATIONSHIPS")
        print("-"*80)
        print(f"Total Relationships: {len(relationships)}")
        for rel in relationships[:5]:
            rel_type = rel.get('type', 'N/A')
            rel_from = rel.get('from', 'N/A')
            rel_to = rel.get('to', [])
            print(f"  - {rel_type}: {rel_from} -> {rel_to}")
        if len(relationships) > 5:
            print(f"  ... and {len(relationships) - 5} more")
        
        print("\n" + "-"*80)
        print("FEATURE CATALOG")
        print("-"*80)
        for comp_type, catalog_info in feature_catalog.items():
            standard = catalog_info.get('standard_features', [])
            new_features = catalog_info.get('new_features_discovered', [])
            print(f"{comp_type}:")
            print(f"  Standard features: {len(standard)}")
            if new_features:
                print(f"  New features discovered: {new_features}")
        
        # Verify output file was created
        components_file = os.path.join(output_dir, "discovered_components.json")
        if os.path.exists(components_file):
            print(f"\n✓ Output file created: {components_file}")
            file_size = os.path.getsize(components_file)
            print(f"  File size: {file_size:,} bytes")
        
        print("\n" + "="*80)
        print("SAMPLE COMPONENT STRUCTURE")
        print("="*80)
        if dashboards:
            sample = dashboards[0]
            print(json.dumps(sample, indent=2))
        elif worksheets:
            sample = worksheets[0]
            print(json.dumps(sample, indent=2))
        
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
        
        return result
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(test_exploration_agent_alone())

