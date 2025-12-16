"""Test script for Parsing Agent - Full workflow test."""
import asyncio
import json
import os
from datetime import datetime
from langgraph.graph import StateGraph, END
from agents.file_analysis_agent import file_analysis_agent
from agents.exploration_agent import exploration_agent
from agents.parsing_agent import parsing_agent
from models.state import AssessmentState
from utils.logger import logger


async def test_parsing_agent():
    """Test full workflow: File Analysis → Exploration → Parsing."""
    
    print("\n" + "="*80)
    print("TESTING PARSING AGENT - FULL WORKFLOW")
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
    job_id = f"test_parsing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = f"output/{job_id}"
    
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
        parsed_filters=None,
        parsed_parameters=None,
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
        # Create workflow: file_analysis -> exploration -> parsing
        test_workflow = StateGraph(AssessmentState)
        test_workflow.add_node("file_analysis", file_analysis_agent)
        test_workflow.add_node("exploration", exploration_agent)
        test_workflow.add_node("parsing", parsing_agent)
        test_workflow.set_entry_point("file_analysis")
        test_workflow.add_edge("file_analysis", "exploration")
        test_workflow.add_edge("exploration", "parsing")
        test_workflow.add_edge("parsing", END)
        
        app = test_workflow.compile()
        logger.info("Test workflow created (file_analysis -> exploration -> parsing)")
        
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
                elif node_name == "exploration":
                    print(f"\n[✓] Exploration Agent completed")
                    discovered = node_state.get('discovered_components', {})
                    if discovered:
                        components = discovered.get('components', {})
                        total = sum(len(v) if isinstance(v, list) else 0 for v in components.values())
                        print(f"  Discovered {total} components")
                        print(f"    - Dashboards: {len(components.get('dashboards', []))}")
                        print(f"    - Worksheets: {len(components.get('worksheets', []))}")
                        print(f"    - Datasources: {len(components.get('datasources', []))}")
                        print(f"    - Calculations: {len(components.get('calculations', []))}")
                        print(f"    - Filters: {len(components.get('filters', []))}")
                        print(f"    - Parameters: {len(components.get('parameters', []))}")
                elif node_name == "parsing":
                    print(f"\n[✓] Parsing Agent completed")
                    final_state = node_state
        
        print("\n" + "="*80)
        print("PARSING RESULTS")
        print("="*80)
        
        # Check parsed components
        parsed_dashboards = final_state.get('parsed_dashboards', [])
        parsed_worksheets = final_state.get('parsed_worksheets', [])
        parsed_datasources = final_state.get('parsed_datasources', [])
        parsed_calculations = final_state.get('parsed_calculations', [])
        parsed_filters = final_state.get('parsed_filters', [])
        parsed_parameters = final_state.get('parsed_parameters', [])
        
        print(f"\nParsed Components:")
        print(f"  - Dashboards: {len(parsed_dashboards)}")
        print(f"  - Worksheets: {len(parsed_worksheets)}")
        print(f"  - Datasources: {len(parsed_datasources)}")
        print(f"  - Calculations: {len(parsed_calculations)}")
        print(f"  - Filters: {len(parsed_filters)}")
        print(f"  - Parameters: {len(parsed_parameters)}")
        
        # Validate structure
        print("\n" + "-"*80)
        print("STRUCTURE VALIDATION")
        print("-"*80)
        
        # Test 1: Verify dashboards have features + structure
        if parsed_dashboards:
            sample_dashboard = parsed_dashboards[0]
            print(f"\n[Test 1] Dashboard Structure:")
            print(f"  ✓ Has 'features': {'features' in sample_dashboard}")
            print(f"  ✓ Has 'structure': {'structure' in sample_dashboard}")
            print(f"  ✓ Has 'dependencies': {'dependencies' in sample_dashboard}")
            if 'structure' in sample_dashboard:
                structure = sample_dashboard['structure']
                print(f"  ✓ Structure has 'layout_type': {'layout_type' in structure}")
                print(f"  ✓ Structure has 'zones': {'zones' in structure}")
        
        # Test 2: Verify worksheets have data_fields structure
        if parsed_worksheets:
            sample_worksheet = parsed_worksheets[0]
            print(f"\n[Test 2] Worksheet Structure:")
            print(f"  ✓ Has 'features': {'features' in sample_worksheet}")
            print(f"  ✓ Has 'structure': {'structure' in sample_worksheet}")
            if 'structure' in sample_worksheet:
                structure = sample_worksheet['structure']
                print(f"  ✓ Structure has 'data_fields': {'data_fields' in structure}")
                print(f"  ✓ Structure has 'chart_type': {'chart_type' in structure}")
        
        # Test 3: Verify datasources have connection details
        if parsed_datasources:
            sample_datasource = parsed_datasources[0]
            print(f"\n[Test 3] Datasource Structure:")
            print(f"  ✓ Has 'features': {'features' in sample_datasource}")
            print(f"  ✓ Has 'structure': {'structure' in sample_datasource}")
            if 'structure' in sample_datasource:
                structure = sample_datasource['structure']
                print(f"  ✓ Structure has 'connection': {'connection' in structure}")
                print(f"  ✓ Structure has 'tables': {'tables' in structure}")
        
        # Test 4: Verify calculations have formula_structure
        if parsed_calculations:
            sample_calc = parsed_calculations[0]
            print(f"\n[Test 4] Calculation Structure:")
            print(f"  ✓ Has 'features': {'features' in sample_calc}")
            print(f"  ✓ Has 'structure': {'structure' in sample_calc}")
            if 'structure' in sample_calc:
                structure = sample_calc['structure']
                print(f"  ✓ Structure has 'formula_structure': {'formula_structure' in structure}")
                print(f"  ✓ Structure has 'dependencies': {'dependencies' in structure}")
        
        # Test 5: Verify filters have applied_to structure (NEW)
        if parsed_filters:
            sample_filter = parsed_filters[0]
            print(f"\n[Test 5] Filter Structure:")
            print(f"  ✓ Has 'features': {'features' in sample_filter}")
            print(f"  ✓ Has 'structure': {'structure' in sample_filter}")
            if 'structure' in sample_filter:
                structure = sample_filter['structure']
                print(f"  ✓ Structure has 'applied_to': {'applied_to' in structure}")
                print(f"  ✓ Structure has 'scope': {'scope' in structure}")
        else:
            print(f"\n[Test 5] Filter Structure: No filters found (skipping)")
        
        # Test 6: Verify parameters have used_by structure (NEW)
        if parsed_parameters:
            sample_param = parsed_parameters[0]
            print(f"\n[Test 6] Parameter Structure:")
            print(f"  ✓ Has 'features': {'features' in sample_param}")
            print(f"  ✓ Has 'structure': {'structure' in sample_param}")
            if 'structure' in sample_param:
                structure = sample_param['structure']
                print(f"  ✓ Structure has 'used_by': {'used_by' in structure}")
                print(f"  ✓ Structure has 'scope': {'scope' in structure}")
        else:
            print(f"\n[Test 6] Parameter Structure: No parameters found (skipping)")
        
        # Test 7: Verify JSON files are created
        print("\n" + "-"*80)
        print("OUTPUT FILES VALIDATION")
        print("-"*80)
        
        output_dir = final_state.get('output_dir')
        if output_dir:
            expected_files = [
                'parsed_dashboards.json',
                'parsed_worksheets.json',
                'parsed_datasources.json',
                'parsed_calculations.json',
                'parsed_filters.json',
                'parsed_parameters.json'
            ]
            
            for filename in expected_files:
                filepath = os.path.join(output_dir, filename)
                exists = os.path.exists(filepath)
                print(f"  {'✓' if exists else '✗'} {filename}: {'Found' if exists else 'Missing'}")
                if exists:
                    # Check file is valid JSON
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            print(f"      - Contains {len(data)} items")
                    except Exception as e:
                        print(f"      - Error reading file: {e}")
        
        # Show sample parsed component
        print("\n" + "="*80)
        print("SAMPLE PARSED COMPONENT")
        print("="*80)
        if parsed_dashboards:
            sample = parsed_dashboards[0]
            print(json.dumps(sample, indent=2))
        elif parsed_worksheets:
            sample = parsed_worksheets[0]
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
    asyncio.run(test_parsing_agent())
