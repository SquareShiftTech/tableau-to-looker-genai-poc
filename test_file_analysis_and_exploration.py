"""Combined test script for File Analysis Agent and Exploration Agent using LangGraph workflow."""
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
    """Test both File Analysis Agent and Exploration Agent together using LangGraph workflow."""
    
    # Test with first file
    initial_state = AssessmentState(
        job_id="test_combined_002",
        source_files=[
            {"platform": "tableau", "file_path": "input_files/tableau/metrics_homepage_metadata.xml"},
        ],
        # Legacy fields (kept for backward compatibility)
        file_analysis_strategy=None,
        strategy_refinement_needed=None,
        strategy_refinement_count=0,
        # New architecture fields
        parsed_elements_paths=None,
        output_dir=None,
        # Component discovery
        discovered_components=None,
        # Parsing outputs
        parsed_metrics=None,
        parsed_dashboards=None,
        parsed_visualizations=None,
        parsed_datasources=None,
        # Specialized agent outputs
        calculation_analysis=None,
        visualization_analysis=None,
        dashboard_analysis=None,
        datasource_analysis=None,
        # Final report
        final_report=None,
        # Status
        status="initial",
        errors=[],
    )
    
    print("\n" + "="*80)
    print("TESTING FILE ANALYSIS + EXPLORATION AGENTS (using LangGraph workflow)")
    print("="*80)
    print(f"File: {initial_state['source_files'][0]['file_path']}")
    print(f"Platform: {initial_state['source_files'][0]['platform']}")
    print("="*80 + "\n")
    
    try:
        # Create a minimal workflow for testing (file_analysis -> exploration only)
        from langgraph.graph import StateGraph, END
        
        test_workflow = StateGraph(AssessmentState)
        test_workflow.add_node("file_analysis", file_analysis_agent)
        test_workflow.add_node("exploration", exploration_agent)
        test_workflow.set_entry_point("file_analysis")
        test_workflow.add_edge("file_analysis", "exploration")
        test_workflow.add_edge("exploration", END)  # Simple linear flow
        
        app = test_workflow.compile()
        logger.info("Test workflow created (file_analysis -> exploration)")
        
        # Run workflow
        print("\n" + "-"*80)
        print("RUNNING WORKFLOW (file_analysis -> exploration)")
        print("-"*80)
        
        # Use astream to monitor execution
        final_state = initial_state
        
        async for event in app.astream(initial_state):
            for node_name, node_state in event.items():
                if node_name == "file_analysis":
                    print(f"\n[WORKFLOW] → file_analysis node executed")
                    parsed_elements = node_state.get('parsed_elements_paths', [])
                    output_dir = node_state.get('output_dir')
                    if parsed_elements:
                        print(f"  ✓ Extracted {len(parsed_elements)} first-level elements")
                        print(f"     Output directory: {output_dir}")
                        for elem in parsed_elements[:5]:  # Show first 5
                            print(f"     - {elem.get('element_name')}: {elem.get('size_bytes', 0):,} bytes")
                        if len(parsed_elements) > 5:
                            print(f"     ... and {len(parsed_elements) - 5} more")
                
                elif node_name == "exploration":
                    print(f"\n[WORKFLOW] → exploration node executed")
                    discovered = node_state.get('discovered_components', {})
                    if discovered:
                        dashboards = len(discovered.get('dashboards', []))
                        worksheets = len(discovered.get('worksheets', []))
                        datasources = len(discovered.get('datasources', []))
                        filters = len(discovered.get('filters', []))
                        parameters = len(discovered.get('parameters', []))
                        calculations = len(discovered.get('calculations', []))
                        total = dashboards + worksheets + datasources + filters + parameters + calculations
                        print(f"  ✓ Exploration completed successfully")
                        print(f"     Total components: {total}")
                        print(f"     - Dashboards: {dashboards}")
                        print(f"     - Worksheets: {worksheets}")
                        print(f"     - Datasources: {datasources}")
                        print(f"     - Filters: {filters}")
                        print(f"     - Parameters: {parameters}")
                        print(f"     - Calculations: {calculations}")
                
                # Store final state
                final_state = node_state
        
        # Extract results
        parsed_elements = final_state.get('parsed_elements_paths', [])
        output_dir = final_state.get('output_dir')
        discovered = final_state.get('discovered_components', {}) or {}
        
        print("\n" + "="*80)
        print("FILE ANALYSIS RESULTS")
        print("="*80)
        
        if parsed_elements:
            print(f"\nExtracted {len(parsed_elements)} first-level elements:")
            for elem in parsed_elements:
                print(f"  - {elem.get('element_name')}: {elem.get('file_path')} ({elem.get('size_bytes', 0):,} bytes)")
            print(f"\nOutput directory: {output_dir}")
        else:
            print("\n✗ No parsed elements found")
        
        print("\n" + "="*80)
        print("EXPLORATION RESULTS")
        print("="*80)
        
        dashboards = discovered.get('dashboards', [])
        worksheets = discovered.get('worksheets', [])
        datasources = discovered.get('datasources', [])
        filters = discovered.get('filters', [])
        parameters = discovered.get('parameters', [])
        calculations = discovered.get('calculations', [])
        
        print(f"\nDashboards: {len(dashboards)}")
        for dash in dashboards[:5]:  # Show first 5
            print(f"  - {dash.get('name', 'N/A')} (id: {dash.get('id', 'N/A')})")
        if len(dashboards) > 5:
            print(f"  ... and {len(dashboards) - 5} more")
        
        print(f"\nWorksheets: {len(worksheets)}")
        for ws in worksheets[:5]:  # Show first 5
            print(f"  - {ws.get('name', 'N/A')} ({ws.get('type', 'N/A')}) (id: {ws.get('id', 'N/A')})")
        if len(worksheets) > 5:
            print(f"  ... and {len(worksheets) - 5} more")
        
        print(f"\nData Sources: {len(datasources)}")
        for ds in datasources[:5]:  # Show first 5
            print(f"  - {ds.get('name', 'N/A')} ({ds.get('type', 'N/A')}) (id: {ds.get('id', 'N/A')})")
        if len(datasources) > 5:
            print(f"  ... and {len(datasources) - 5} more")
        
        print(f"\nFilters: {len(filters)}")
        print(f"Parameters: {len(parameters)}")
        print(f"Calculations: {len(calculations)}")
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        total = len(dashboards) + len(worksheets) + len(datasources) + len(filters) + len(parameters) + len(calculations)
        print(f"Total Components Discovered: {total}")
        print(f"  - Dashboards: {len(dashboards)}")
        print(f"  - Worksheets: {len(worksheets)}")
        print(f"  - Data Sources: {len(datasources)}")
        print(f"  - Filters: {len(filters)}")
        print(f"  - Parameters: {len(parameters)}")
        print(f"  - Calculations: {len(calculations)}")
        
        if not parsed_elements:
            print("\n✗ No parsed elements found in final state")
            if final_state.get('errors'):
                print(f"  Errors: {final_state['errors']}")
            return
        
        print("\n" + "="*80)
        print("FULL COMPONENTS JSON (first 2000 chars):")
        print("="*80)
        components_json = json.dumps(discovered, indent=2)
        print(components_json[:2000] + "..." if len(components_json) > 2000 else components_json)
        print("="*80)
        
        # Write outputs to files
        print("\n" + "="*80)
        print("WRITING OUTPUTS TO FILES")
        print("="*80)
        
        # Use output_dir from state, or create default
        if not output_dir:
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename based on job_id and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{final_state['job_id']}_{timestamp}"
        
        # Write discovered components to file
        components_file = os.path.join(output_dir, f"{base_filename}_components.json")
        with open(components_file, 'w', encoding='utf-8') as f:
            json.dump(discovered, f, indent=2)
        print(f"✓ Components written to: {components_file}")
        
        # Write parsed elements info
        if parsed_elements:
            elements_file = os.path.join(output_dir, f"{base_filename}_elements.json")
            with open(elements_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_elements, f, indent=2)
            print(f"✓ Parsed elements info written to: {elements_file}")
        
        # Write summary report
        summary_file = os.path.join(output_dir, f"{base_filename}_summary.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("FILE ANALYSIS + EXPLORATION AGENT OUTPUT SUMMARY\n")
            f.write("="*80 + "\n\n")
            f.write(f"Job ID: {final_state['job_id']}\n")
            f.write(f"File: {final_state['source_files'][0]['file_path']}\n")
            f.write(f"Platform: {final_state['source_files'][0]['platform']}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("-"*80 + "\n")
            f.write("FILE ANALYSIS RESULTS\n")
            f.write("-"*80 + "\n")
            f.write(f"Parsed Elements: {len(parsed_elements)}\n")
            f.write(f"Output Directory: {output_dir}\n\n")
            f.write("-"*80 + "\n")
            f.write("COMPONENT COUNTS\n")
            f.write("-"*80 + "\n")
            f.write(f"Total Components: {total}\n")
            f.write(f"  - Dashboards: {len(dashboards)}\n")
            f.write(f"  - Worksheets: {len(worksheets)}\n")
            f.write(f"  - Data Sources: {len(datasources)}\n")
            f.write(f"  - Filters: {len(filters)}\n")
            f.write(f"  - Parameters: {len(parameters)}\n")
            f.write(f"  - Calculations: {len(calculations)}\n")
            if final_state.get('errors'):
                f.write("\n" + "-"*80 + "\n")
                f.write("ERRORS\n")
                f.write("-"*80 + "\n")
                for error in final_state['errors']:
                    f.write(f"  - {error}\n")
        print(f"✓ Summary written to: {summary_file}")
        
        print("\n" + "="*80)
        print("OUTPUT FILES CREATED:")
        print("="*80)
        print(f"  Components: {components_file}")
        if parsed_elements:
            print(f"  Elements Info: {elements_file}")
        print(f"  Summary: {summary_file}")
        print("="*80)
        
        if final_state.get('errors'):
            print(f"\nErrors: {final_state['errors']}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    asyncio.run(test_file_analysis_and_exploration())

