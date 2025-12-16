"""Test script for File Analysis Agent + Exploration Agent using new design."""
import asyncio
import json
import os
from datetime import datetime
from langgraph.graph import StateGraph, END
from agents.file_analysis_agent import file_analysis_agent
from agents.exploration_agent import exploration_agent
from models.state import AssessmentState
from utils.logger import logger


async def test_file_analysis_and_exploration():
    """Test both File Analysis Agent and Exploration Agent together."""
    
    print("\n" + "="*80)
    print("TESTING FILE ANALYSIS + EXPLORATION AGENTS (New Design)")
    print("="*80)
    
    # Test file
    test_file = "input_files/tableau/sales_summary_final.xml"
    
    if not os.path.exists(test_file):
        print(f"\n✗ Test file not found: {test_file}")
        print("Please ensure the test file exists.")
        return
    
    file_size = os.path.getsize(test_file)
    print(f"\nTest File: {test_file}")
    print(f"File Size: {file_size:,} bytes ({file_size/1024:.2f} KB)")
    
    # Create initial state
    job_id = f"test_combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    initial_state = AssessmentState(
        job_id=job_id,
        source_files=[
            {"platform": "tableau", "file_path": test_file},
        ],
        file_analysis_strategy=None,
        strategy_refinement_needed=None,
        strategy_refinement_count=0,
        parsed_elements_paths=None,
        output_dir=None,
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
        status="initial",
        errors=[],
    )
    
    print(f"Job ID: {job_id}")
    print(f"Platform: {initial_state['source_files'][0]['platform']}")
    
    try:
        # Create workflow: file_analysis -> exploration
        test_workflow = StateGraph(AssessmentState)
        test_workflow.add_node("file_analysis", file_analysis_agent)
        test_workflow.add_node("exploration", exploration_agent)
        test_workflow.set_entry_point("file_analysis")
        test_workflow.add_edge("file_analysis", "exploration")
        test_workflow.add_edge("exploration", END)
        
        app = test_workflow.compile()
        logger.info("Test workflow created (file_analysis -> exploration)")
        
        print("\n" + "-"*80)
        print("RUNNING WORKFLOW")
        print("-"*80)
        
        # Run workflow
        final_state = initial_state
        async for event in app.astream(initial_state):
            for node_name, node_state in event.items():
                if node_name == "file_analysis":
                    print(f"\n[✓] File Analysis Agent completed")
                    parsed_elements = node_state.get('parsed_elements_paths', [])
                    output_dir = node_state.get('output_dir')
                    if parsed_elements:
                        print(f"  Extracted {len(parsed_elements)} files")
                        print(f"  Output directory: {output_dir}")
                        # Show file sizes
                        total_size = sum(e.get('size_bytes', 0) for e in parsed_elements)
                        print(f"  Total size: {total_size:,} bytes ({total_size/1024:.2f} KB)")
                        # Show first few files
                        for elem in parsed_elements[:5]:
                            file_path = elem.get('file_path', 'N/A')
                            size = elem.get('size_bytes', 0)
                            filename = os.path.basename(file_path) if file_path != 'N/A' else 'N/A'
                            print(f"    - {filename}: {size:,} bytes")
                        if len(parsed_elements) > 5:
                            print(f"    ... and {len(parsed_elements) - 5} more files")
                
                elif node_name == "exploration":
                    print(f"\n[✓] Exploration Agent completed")
                    discovered = node_state.get('discovered_components', {})
                    if discovered:
                        components = discovered.get('components', {})
                        metadata = discovered.get('discovery_metadata', {})
                        
                        dashboards = len(components.get('dashboards', []))
                        worksheets = len(components.get('worksheets', []))
                        datasources = len(components.get('datasources', []))
                        calculations = len(components.get('calculations', []))
                        filters = len(components.get('filters', []))
                        parameters = len(components.get('parameters', []))
                        
                        print(f"  Files processed: {metadata.get('total_files_processed', 0)}")
                        print(f"  Files skipped: {metadata.get('total_files_skipped', 0)}")
                        print(f"  Components discovered:")
                        print(f"    - Dashboards: {dashboards}")
                        print(f"    - Worksheets: {worksheets}")
                        print(f"    - Datasources: {datasources}")
                        print(f"    - Calculations: {calculations}")
                        print(f"    - Filters: {filters}")
                        print(f"    - Parameters: {parameters}")
                        
                        relationships = discovered.get('relationships', [])
                        print(f"  Relationships: {len(relationships)}")
                
                final_state = node_state
        
        # Extract results
        parsed_elements = final_state.get('parsed_elements_paths', [])
        output_dir = final_state.get('output_dir')
        discovered = final_state.get('discovered_components', {}) or {}
        
        print("\n" + "="*80)
        print("DETAILED RESULTS")
        print("="*80)
        
        # File Analysis Results
        print("\n--- FILE ANALYSIS RESULTS ---")
        if parsed_elements:
            print(f"✓ Extracted {len(parsed_elements)} files")
            print(f"  Output directory: {output_dir}")
            
            # Check size threshold compliance
            from config.settings import get_settings
            settings = get_settings()
            threshold = settings.chunk_max_size_bytes
            
            all_within_threshold = all(
                e.get('size_bytes', 0) <= threshold
                for e in parsed_elements
            )
            print(f"  All files ≤ {threshold:,} bytes: {all_within_threshold}")
            
            if not all_within_threshold:
                large_files = [
                    e for e in parsed_elements
                    if e.get('size_bytes', 0) > threshold
                ]
                print(f"  ⚠ {len(large_files)} files exceed threshold:")
                for f in large_files:
                    print(f"    - {os.path.basename(f.get('file_path', 'N/A'))}: {f.get('size_bytes', 0):,} bytes")
        else:
            print("✗ No parsed elements found")
        
        # Exploration Results
        print("\n--- EXPLORATION RESULTS ---")
        if discovered:
            platform = discovered.get('platform', 'unknown')
            metadata = discovered.get('discovery_metadata', {})
            components = discovered.get('components', {})
            relationships = discovered.get('relationships', [])
            feature_catalog = discovered.get('feature_catalog', {})
            
            print(f"Platform: {platform}")
            print(f"Files Processed: {metadata.get('total_files_processed', 0)}")
            print(f"Files Skipped: {metadata.get('total_files_skipped', 0)}")
            
            dashboards = components.get('dashboards', [])
            worksheets = components.get('worksheets', [])
            datasources = components.get('datasources', [])
            calculations = components.get('calculations', [])
            filters = components.get('filters', [])
            parameters = components.get('parameters', [])
            
            print(f"\nComponents:")
            print(f"  Dashboards: {len(dashboards)}")
            for dash in dashboards[:3]:
                print(f"    - {dash.get('name', 'N/A')} (id: {dash.get('id', 'N/A')})")
                features = dash.get('features_to_extract', [])
                if features:
                    print(f"      Features: {', '.join(features[:3])}{'...' if len(features) > 3 else ''}")
            if len(dashboards) > 3:
                print(f"    ... and {len(dashboards) - 3} more")
            
            print(f"\n  Worksheets: {len(worksheets)}")
            for ws in worksheets[:3]:
                print(f"    - {ws.get('name', 'N/A')} (id: {ws.get('id', 'N/A')})")
                features = ws.get('features_to_extract', [])
                if features:
                    print(f"      Features: {', '.join(features[:3])}{'...' if len(features) > 3 else ''}")
            if len(worksheets) > 3:
                print(f"    ... and {len(worksheets) - 3} more")
            
            print(f"\n  Datasources: {len(datasources)}")
            for ds in datasources[:3]:
                print(f"    - {ds.get('name', 'N/A')} (id: {ds.get('id', 'N/A')})")
            if len(datasources) > 3:
                print(f"    ... and {len(datasources) - 3} more")
            
            print(f"\n  Calculations: {len(calculations)}")
            print(f"  Filters: {len(filters)}")
            print(f"  Parameters: {len(parameters)}")
            
            print(f"\nRelationships: {len(relationships)}")
            for rel in relationships[:5]:
                print(f"  - {rel.get('type', 'N/A')}: {rel.get('from', 'N/A')} -> {rel.get('to', [])}")
            if len(relationships) > 5:
                print(f"  ... and {len(relationships) - 5} more")
            
            # Check if output file exists
            if output_dir:
                components_file = os.path.join(output_dir, "discovered_components.json")
                if os.path.exists(components_file):
                    print(f"\n✓ Output file: {components_file}")
                    file_size = os.path.getsize(components_file)
                    print(f"  File size: {file_size:,} bytes")
        else:
            print("✗ No components discovered")
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        if discovered:
            components = discovered.get('components', {})
            total = sum(len(v) if isinstance(v, list) else 0 for v in components.values())
            print(f"Total Components: {total}")
            print(f"  - Dashboards: {len(components.get('dashboards', []))}")
            print(f"  - Worksheets: {len(components.get('worksheets', []))}")
            print(f"  - Datasources: {len(components.get('datasources', []))}")
            print(f"  - Calculations: {len(components.get('calculations', []))}")
            print(f"  - Filters: {len(components.get('filters', []))}")
            print(f"  - Parameters: {len(components.get('parameters', []))}")
            print(f"  - Relationships: {len(discovered.get('relationships', []))}")
        
        if final_state.get('errors'):
            print(f"\n⚠ Errors: {len(final_state['errors'])}")
            for error in final_state['errors']:
                print(f"  - {error}")
        
        # Show sample component structure
        if discovered:
            components = discovered.get('components', {})
            print("\n" + "="*80)
            print("SAMPLE COMPONENT STRUCTURE")
            print("="*80)
            if components.get('dashboards'):
                sample = components['dashboards'][0]
                print(json.dumps(sample, indent=2))
            elif components.get('worksheets'):
                sample = components['worksheets'][0]
                print(json.dumps(sample, indent=2))
        
        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)
        
        return final_state
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(test_file_analysis_and_exploration())

