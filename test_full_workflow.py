"""Comprehensive test script for full workflow: File Analysis -> Exploration -> Parsing -> Complexity Analysis -> BigQuery."""
import asyncio
import json
import os
from datetime import datetime
from workflows.assessment_workflow import create_assessment_workflow
from models.state import AssessmentState
from utils.logger import logger


async def test_full_workflow():
    """Test the complete workflow from file analysis to BigQuery writes."""
    
    # Test with a file
    initial_state = AssessmentState(
        job_id="test_full_workflow_001",
        source_files=[
            {"platform": "tableau", "file_path": "input_files/tableau/sales_summary_final.xml"},
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
        parsed_worksheets=None,
        parsed_calculations=None,
        # Specialized agent outputs
        calculation_analysis=None,
        visualization_analysis=None,
        dashboard_analysis=None,
        datasource_analysis=None,
        worksheet_analysis=None,
        # Final report
        final_report=None,
        # Status
        status="initial",
        errors=[],
    )
    
    print("\n" + "="*80)
    print("TESTING FULL WORKFLOW")
    print("="*80)
    print(f"File: {initial_state['source_files'][0]['file_path']}")
    print(f"Platform: {initial_state['source_files'][0]['platform']}")
    print(f"Job ID: {initial_state['job_id']}")
    print("="*80 + "\n")
    
    try:
        # Use the actual workflow (handles parallel execution correctly)
        app = create_assessment_workflow()
        logger.info("Using actual assessment workflow")
        
        # Run workflow using ainvoke (properly handles parallel state updates)
        print("\n" + "-"*80)
        print("RUNNING FULL WORKFLOW")
        print("-"*80)
        print("\n[WORKFLOW] Executing workflow...")
        
        final_state = await app.ainvoke(initial_state)
        
        print("\n[WORKFLOW] Workflow completed successfully!")
        
        # Show execution summary
        print("\n" + "-"*80)
        print("EXECUTION SUMMARY")
        print("-"*80)
        parsed_elements = final_state.get('parsed_elements_paths', [])
        discovered = final_state.get('discovered_components', {}) or {}
        parsed_dashboards = final_state.get('parsed_dashboards', [])
        parsed_worksheets = final_state.get('parsed_worksheets', [])
        parsed_datasources = final_state.get('parsed_datasources', [])
        parsed_calculations = final_state.get('parsed_calculations', [])
        dashboard_analysis = final_state.get('dashboard_analysis', [])
        worksheet_analysis = final_state.get('worksheet_analysis', [])
        datasource_analysis = final_state.get('datasource_analysis', [])
        calculation_analysis = final_state.get('calculation_analysis', [])
        
        print(f"✓ File Analysis: {len(parsed_elements)} elements extracted")
        print(f"✓ Exploration: {len(discovered.get('dashboards', []))} dashboards, {len(discovered.get('worksheets', []))} worksheets discovered")
        print(f"✓ Parsing: {len(parsed_dashboards)} dashboards, {len(parsed_worksheets)} worksheets, {len(parsed_datasources)} datasources, {len(parsed_calculations)} calculations parsed")
        print(f"✓ Complexity Analysis: {len(dashboard_analysis)} dashboards, {len(worksheet_analysis)} worksheets, {len(datasource_analysis)} datasources, {len(calculation_analysis)} calculations analyzed")
        
        # Extract and display results
        print("\n" + "="*80)
        print("FULL WORKFLOW RESULTS")
        print("="*80)
        
        # File Analysis Results
        parsed_elements = final_state.get('parsed_elements_paths', [])
        output_dir = final_state.get('output_dir')
        print(f"\n[FILE ANALYSIS]")
        print(f"  Parsed Elements: {len(parsed_elements)}")
        print(f"  Output Directory: {output_dir}")
        
        # Exploration Results
        discovered = final_state.get('discovered_components', {}) or {}
        print(f"\n[EXPLORATION]")
        print(f"  Dashboards: {len(discovered.get('dashboards', []))}")
        print(f"  Worksheets: {len(discovered.get('worksheets', []))}")
        print(f"  Datasources: {len(discovered.get('datasources', []))}")
        print(f"  Filters: {len(discovered.get('filters', []))}")
        print(f"  Parameters: {len(discovered.get('parameters', []))}")
        print(f"  Calculations: {len(discovered.get('calculations', []))}")
        
        # Parsing Results
        parsed_dashboards = final_state.get('parsed_dashboards', [])
        parsed_worksheets = final_state.get('parsed_worksheets', [])
        parsed_datasources = final_state.get('parsed_datasources', [])
        parsed_calculations = final_state.get('parsed_calculations', [])
        print(f"\n[PARSING]")
        print(f"  Parsed Dashboards: {len(parsed_dashboards)}")
        print(f"  Parsed Worksheets: {len(parsed_worksheets)}")
        print(f"  Parsed Datasources: {len(parsed_datasources)}")
        print(f"  Parsed Calculations: {len(parsed_calculations)}")
        if parsed_dashboards:
            workbook_name = parsed_dashboards[0].get('workbook_name', 'N/A')
            print(f"  Workbook Name: {workbook_name}")
        
        # Complexity Analysis Results
        dashboard_analysis = final_state.get('dashboard_analysis', [])
        worksheet_analysis = final_state.get('worksheet_analysis', [])
        datasource_analysis = final_state.get('datasource_analysis', [])
        calculation_analysis = final_state.get('calculation_analysis', [])
        print(f"\n[COMPLEXITY ANALYSIS]")
        print(f"  Dashboard Analysis: {len(dashboard_analysis)} records")
        print(f"  Worksheet Analysis: {len(worksheet_analysis)} records")
        print(f"  Datasource Analysis: {len(datasource_analysis)} records")
        print(f"  Calculation Analysis: {len(calculation_analysis)} records")
        
        # Display sample records
        print("\n" + "="*80)
        print("SAMPLE RECORDS")
        print("="*80)
        
        if dashboard_analysis:
            print("\n[DASHBOARD SAMPLE]")
            sample = dashboard_analysis[0]
            print(f"  Workbook: {sample.get('workbook_name')}")
            print(f"  Name: {sample.get('name')}")
            print(f"  ID: {sample.get('id')}")
            print(f"  Complexity: {sample.get('complexity')}")
            print(f"  Features: {json.dumps(sample.get('features', {}), indent=4)}")
            print(f"  Dependencies: {json.dumps(sample.get('dependencies', {}), indent=4)}")
        
        if worksheet_analysis:
            print("\n[WORKSHEET SAMPLE]")
            sample = worksheet_analysis[0]
            print(f"  Name: {sample.get('name')}")
            print(f"  ID: {sample.get('id')}")
            print(f"  Complexity: {sample.get('complexity')}")
            print(f"  Features: {json.dumps(sample.get('features', {}), indent=4)}")
        
        if datasource_analysis:
            print("\n[DATASOURCE SAMPLE]")
            sample = datasource_analysis[0]
            print(f"  Name: {sample.get('name')}")
            print(f"  ID: {sample.get('id')}")
            print(f"  Type: {sample.get('type')}")
            print(f"  Complexity: {sample.get('complexity')}")
        
        if calculation_analysis:
            print("\n[CALCULATION SAMPLE]")
            sample = calculation_analysis[0]
            print(f"  Datasource ID: {sample.get('datasource_id')}")
            print(f"  Field Name: {sample.get('field_name')}")
            print(f"  Formula: {sample.get('formula', 'N/A')[:100]}...")
            print(f"  Complexity: {sample.get('complexity')}")
        
        # Write outputs to files
        print("\n" + "="*80)
        print("WRITING OUTPUTS TO FILES")
        print("="*80)
        
        if not output_dir:
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{final_state['job_id']}_{timestamp}"
        
        # Write all analysis results
        if dashboard_analysis:
            dashboard_file = os.path.join(output_dir, f"{base_filename}_dashboard_analysis.json")
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                json.dump(dashboard_analysis, f, indent=2)
            print(f"✓ Dashboard analysis: {dashboard_file}")
        
        if worksheet_analysis:
            worksheet_file = os.path.join(output_dir, f"{base_filename}_worksheet_analysis.json")
            with open(worksheet_file, 'w', encoding='utf-8') as f:
                json.dump(worksheet_analysis, f, indent=2)
            print(f"✓ Worksheet analysis: {worksheet_file}")
        
        if datasource_analysis:
            datasource_file = os.path.join(output_dir, f"{base_filename}_datasource_analysis.json")
            with open(datasource_file, 'w', encoding='utf-8') as f:
                json.dump(datasource_analysis, f, indent=2)
            print(f"✓ Datasource analysis: {datasource_file}")
        
        if calculation_analysis:
            calculation_file = os.path.join(output_dir, f"{base_filename}_calculation_analysis.json")
            with open(calculation_file, 'w', encoding='utf-8') as f:
                json.dump(calculation_analysis, f, indent=2)
            print(f"✓ Calculation analysis: {calculation_file}")
        
        # Write parsed data
        if parsed_dashboards:
            parsed_dashboards_file = os.path.join(output_dir, f"{base_filename}_parsed_dashboards.json")
            with open(parsed_dashboards_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_dashboards, f, indent=2)
            print(f"✓ Parsed dashboards: {parsed_dashboards_file}")
        
        if parsed_worksheets:
            parsed_worksheets_file = os.path.join(output_dir, f"{base_filename}_parsed_worksheets.json")
            with open(parsed_worksheets_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_worksheets, f, indent=2)
            print(f"✓ Parsed worksheets: {parsed_worksheets_file}")
        
        if parsed_datasources:
            parsed_datasources_file = os.path.join(output_dir, f"{base_filename}_parsed_datasources.json")
            with open(parsed_datasources_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_datasources, f, indent=2)
            print(f"✓ Parsed datasources: {parsed_datasources_file}")
        
        if parsed_calculations:
            parsed_calculations_file = os.path.join(output_dir, f"{base_filename}_parsed_calculations.json")
            with open(parsed_calculations_file, 'w', encoding='utf-8') as f:
                json.dump(parsed_calculations, f, indent=2)
            print(f"✓ Parsed calculations: {parsed_calculations_file}")
        
        # Write summary report
        summary_file = os.path.join(output_dir, f"{base_filename}_summary.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("FULL WORKFLOW TEST SUMMARY\n")
            f.write("="*80 + "\n\n")
            f.write(f"Job ID: {final_state['job_id']}\n")
            f.write(f"File: {final_state['source_files'][0]['file_path']}\n")
            f.write(f"Platform: {final_state['source_files'][0]['platform']}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("-"*80 + "\n")
            f.write("FILE ANALYSIS\n")
            f.write("-"*80 + "\n")
            f.write(f"Parsed Elements: {len(parsed_elements)}\n")
            f.write(f"Output Directory: {output_dir}\n\n")
            
            f.write("-"*80 + "\n")
            f.write("EXPLORATION\n")
            f.write("-"*80 + "\n")
            f.write(f"Dashboards: {len(discovered.get('dashboards', []))}\n")
            f.write(f"Worksheets: {len(discovered.get('worksheets', []))}\n")
            f.write(f"Datasources: {len(discovered.get('datasources', []))}\n")
            f.write(f"Filters: {len(discovered.get('filters', []))}\n")
            f.write(f"Parameters: {len(discovered.get('parameters', []))}\n")
            f.write(f"Calculations: {len(discovered.get('calculations', []))}\n\n")
            
            f.write("-"*80 + "\n")
            f.write("PARSING\n")
            f.write("-"*80 + "\n")
            f.write(f"Parsed Dashboards: {len(parsed_dashboards)}\n")
            f.write(f"Parsed Worksheets: {len(parsed_worksheets)}\n")
            f.write(f"Parsed Datasources: {len(parsed_datasources)}\n")
            f.write(f"Parsed Calculations: {len(parsed_calculations)}\n")
            if parsed_dashboards:
                f.write(f"Workbook Name: {parsed_dashboards[0].get('workbook_name', 'N/A')}\n")
            f.write("\n")
            
            f.write("-"*80 + "\n")
            f.write("COMPLEXITY ANALYSIS\n")
            f.write("-"*80 + "\n")
            f.write(f"Dashboard Analysis: {len(dashboard_analysis)}\n")
            f.write(f"Worksheet Analysis: {len(worksheet_analysis)}\n")
            f.write(f"Datasource Analysis: {len(datasource_analysis)}\n")
            f.write(f"Calculation Analysis: {len(calculation_analysis)}\n\n")
            
            # Complexity breakdown
            if dashboard_analysis:
                f.write("Dashboard Complexity:\n")
                complexities = {}
                for dash in dashboard_analysis:
                    comp = dash.get('complexity', 'unknown')
                    complexities[comp] = complexities.get(comp, 0) + 1
                for comp, count in complexities.items():
                    f.write(f"  - {comp}: {count}\n")
                f.write("\n")
            
            if final_state.get('errors'):
                f.write("-"*80 + "\n")
                f.write("ERRORS\n")
                f.write("-"*80 + "\n")
                for error in final_state['errors']:
                    f.write(f"  - {error}\n")
        
        print(f"✓ Summary: {summary_file}")
        
        print("\n" + "="*80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("="*80)
        
        if final_state.get('errors'):
            print(f"\n⚠ Warnings/Errors: {final_state['errors']}")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_full_workflow())

