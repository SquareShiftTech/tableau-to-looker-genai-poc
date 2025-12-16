"""Simple standalone test for File Analysis Agent."""
import asyncio
import json
import os
from agents.file_analysis_agent import file_analysis_agent
from models.state import AssessmentState
from utils.logger import logger


async def test_file_analysis_simple():
    """Simple test for File Analysis Agent."""
    
    print("\n" + "="*80)
    print("FILE ANALYSIS AGENT - SIMPLE TEST")
    print("="*80)
    
    # Check if test file exists
    test_file = "input_files/tableau/sales_summary_final.xml"
    if not os.path.exists(test_file):
        print(f"\n✗ Test file not found: {test_file}")
        print("Please ensure the test file exists.")
        return
    
    print(f"\nTest File: {test_file}")
    print(f"File exists: {os.path.exists(test_file)}")
    
    if os.path.exists(test_file):
        file_size = os.path.getsize(test_file)
        print(f"File size: {file_size:,} bytes ({file_size/1024:.2f} KB)")
    
    # Create state
    state = AssessmentState(
        job_id="test_simple_001",
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
    
    print("\n" + "-"*80)
    print("Running File Analysis Agent...")
    print("-"*80)
    
    try:
        result = await file_analysis_agent(state)
        
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)
        
        print(f"\nStatus: {result.get('status')}")
        print(f"Output Directory: {result.get('output_dir')}")
        
        parsed_elements = result.get('parsed_elements_paths', [])
        print(f"\nNumber of files created: {len(parsed_elements)}")
        
        if parsed_elements:
            print("\nFiles Created:")
            print("-"*80)
            total_size = 0
            for i, elem in enumerate(parsed_elements, 1):
                file_path = elem.get('file_path', 'N/A')
                size_bytes = elem.get('size_bytes', 0)
                total_size += size_bytes
                file_exists = os.path.exists(file_path) if file_path != 'N/A' else False
                
                # Show relative path for readability
                rel_path = os.path.relpath(file_path) if file_path != 'N/A' else 'N/A'
                
                print(f"\n{i}. {rel_path}")
                print(f"   Size: {size_bytes:,} bytes ({size_bytes/1024:.2f} KB)")
                print(f"   Exists: {file_exists}")
            
            print("\n" + "-"*80)
            print(f"Total size: {total_size:,} bytes ({total_size/1024:.2f} KB)")
            
            # Check size threshold
            from config.settings import get_settings
            settings = get_settings()
            threshold = settings.chunk_max_size_bytes
            print(f"Size threshold: {threshold:,} bytes ({threshold/1024:.2f} KB)")
            
            # Verify all files are within threshold
            all_within_threshold = all(
                elem.get('size_bytes', 0) <= threshold
                for elem in parsed_elements
            )
            print(f"\n✓ All files ≤ threshold: {all_within_threshold}")
            
            # Verify all files exist
            all_exist = all(
                os.path.exists(elem.get('file_path', ''))
                for elem in parsed_elements
            )
            print(f"✓ All files exist: {all_exist}")
        
        if result.get('errors'):
            print(f"\n⚠ Errors ({len(result['errors'])}):")
            for error in result['errors']:
                print(f"  - {error}")
        
        print("\n" + "="*80)
        print("JSON OUTPUT (first 3 files):")
        print("="*80)
        if parsed_elements:
            print(json.dumps(parsed_elements[:3], indent=2))
            if len(parsed_elements) > 3:
                print(f"\n... and {len(parsed_elements) - 3} more files")
        
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
    asyncio.run(test_file_analysis_simple())

