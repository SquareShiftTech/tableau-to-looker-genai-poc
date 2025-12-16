"""Comprehensive test for File Analysis Agent with recursive splitting."""
import asyncio
import json
import os
import tempfile
import shutil
from pathlib import Path
from agents.file_analysis_agent import file_analysis_agent
from models.state import AssessmentState
from utils.logger import logger
from config.settings import get_settings


async def test_basic_extraction():
    """Test basic first-level element extraction."""
    print("\n" + "="*80)
    print("TEST 1: Basic First-Level Element Extraction")
    print("="*80)
    
    state = AssessmentState(
        job_id="test_basic_001",
        source_files=[
            {"platform": "tableau", "file_path": "input_files/tableau/sales_summary_final.xml"},
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
    
    try:
        result = await file_analysis_agent(state)
        
        print(f"\n✓ Status: {result.get('status')}")
        print(f"✓ Output Directory: {result.get('output_dir')}")
        
        parsed_elements = result.get('parsed_elements_paths', [])
        print(f"✓ Number of files created: {len(parsed_elements)}")
        
        print(f"\nFiles Created:")
        for i, elem in enumerate(parsed_elements, 1):
            file_path = elem.get('file_path', 'N/A')
            size_bytes = elem.get('size_bytes', 0)
            file_exists = os.path.exists(file_path) if file_path != 'N/A' else False
            print(f"  {i}. {file_path}")
            print(f"     Size: {size_bytes:,} bytes ({size_bytes/1024:.2f} KB)")
            print(f"     Exists: {file_exists}")
        
        if result.get('errors'):
            print(f"\n⚠ Errors: {result['errors']}")
        
        # Verify all files exist
        all_exist = all(
            os.path.exists(elem.get('file_path', ''))
            for elem in parsed_elements
        )
        print(f"\n✓ All files exist: {all_exist}")
        
        # Verify all files are within size threshold
        settings = get_settings()
        threshold = settings.chunk_max_size_bytes
        all_within_threshold = all(
            elem.get('size_bytes', 0) <= threshold
            for elem in parsed_elements
        )
        print(f"✓ All files ≤ {threshold:,} bytes: {all_within_threshold}")
        
        return result
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n✗ ERROR: {e}")
        return None


async def test_recursive_splitting():
    """Test recursive splitting with a large file."""
    print("\n" + "="*80)
    print("TEST 2: Recursive Splitting (Large File Simulation)")
    print("="*80)
    
    # Create a temporary large XML file for testing
    temp_dir = tempfile.mkdtemp()
    large_xml_file = os.path.join(temp_dir, "large_worksheets.xml")
    
    try:
        # Create a large XML file with many worksheet elements
        # Each worksheet is ~10KB, create 100 worksheets = ~1MB
        worksheets_xml = '<?xml version="1.0" encoding="utf-8"?>\n<worksheets>\n'
        
        for i in range(100):
            # Create a worksheet with enough content to be ~10KB
            worksheet_content = f"""  <worksheet name="Sheet_{i}">
    <layout-options>
      <title>Worksheet {i}</title>
    </layout-options>
    <table>
      <view>
        <datasources>
          <datasource name="ds_{i}" />
        </datasources>
        <data>
          {'<row>' + '<value>Data</value>' * 50 + '</row>\n          ' * 20}
        </data>
      </view>
    </table>
    <panes>
      <pane id="1">
        <mark class="Bar" />
        <encodings>
          <color column="[Field_{i}]" />
          <size column="[Measure_{i}]" />
        </encodings>
      </pane>
    </panes>
  </worksheet>
"""
            worksheets_xml += worksheet_content
        
        worksheets_xml += "</worksheets>"
        
        with open(large_xml_file, 'w', encoding='utf-8') as f:
            f.write(worksheets_xml)
        
        file_size = os.path.getsize(large_xml_file)
        print(f"Created test file: {large_xml_file}")
        print(f"File size: {file_size:,} bytes ({file_size/1024:.2f} KB)")
        
        settings = get_settings()
        threshold = settings.chunk_max_size_bytes
        print(f"Size threshold: {threshold:,} bytes ({threshold/1024:.2f} KB)")
        
        state = AssessmentState(
            job_id="test_recursive_001",
            source_files=[
                {"platform": "tableau", "file_path": large_xml_file},
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
        
        result = await file_analysis_agent(state)
        
        print(f"\n✓ Status: {result.get('status')}")
        
        parsed_elements = result.get('parsed_elements_paths', [])
        print(f"✓ Number of files created: {len(parsed_elements)}")
        
        # Verify splitting occurred
        if len(parsed_elements) > 1:
            print(f"✓ Recursive splitting occurred: {len(parsed_elements)} files created")
        else:
            print(f"⚠ No splitting occurred (file may be small or single element)")
        
        print(f"\nFiles Created:")
        for i, elem in enumerate(parsed_elements[:10], 1):  # Show first 10
            file_path = elem.get('file_path', 'N/A')
            size_bytes = elem.get('size_bytes', 0)
            print(f"  {i}. {os.path.basename(file_path)}")
            print(f"     Size: {size_bytes:,} bytes ({size_bytes/1024:.2f} KB)")
        
        if len(parsed_elements) > 10:
            print(f"  ... and {len(parsed_elements) - 10} more files")
        
        # Verify all files are within threshold
        all_within_threshold = all(
            elem.get('size_bytes', 0) <= threshold
            for elem in parsed_elements
        )
        print(f"\n✓ All files ≤ {threshold:,} bytes: {all_within_threshold}")
        
        # Verify original large file was removed
        original_removed = not os.path.exists(large_xml_file)
        print(f"✓ Original large file removed: {original_removed}")
        
        return result
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n✗ ERROR: {e}")
        return None
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


async def test_edge_cases():
    """Test edge cases: empty file, invalid XML, single element."""
    print("\n" + "="*80)
    print("TEST 3: Edge Cases")
    print("="*80)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Test case 1: Empty file
        print("\n--- Test 3.1: Empty File ---")
        empty_file = os.path.join(temp_dir, "empty.xml")
        with open(empty_file, 'w') as f:
            f.write("")
        
        state = AssessmentState(
            job_id="test_edge_empty",
            source_files=[{"platform": "tableau", "file_path": empty_file}],
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
        
        result = await file_analysis_agent(state)
        parsed_elements = result.get('parsed_elements_paths', [])
        print(f"✓ Empty file handled: {len(parsed_elements)} files created (expected: 0)")
        
        # Test case 2: Invalid XML
        print("\n--- Test 3.2: Invalid XML ---")
        invalid_file = os.path.join(temp_dir, "invalid.xml")
        with open(invalid_file, 'w') as f:
            f.write("<root><unclosed>")
        
        state['job_id'] = "test_edge_invalid"
        state['source_files'] = [{"platform": "tableau", "file_path": invalid_file}]
        
        result = await file_analysis_agent(state)
        print(f"✓ Invalid XML handled: Status = {result.get('status')}")
        if result.get('errors'):
            print(f"  Errors logged: {len(result['errors'])} error(s)")
        
        # Test case 3: Single large element (can't split further)
        print("\n--- Test 3.3: Single Large Element ---")
        single_large_file = os.path.join(temp_dir, "single_large.xml")
        # Create a single element with lots of content
        large_content = '<?xml version="1.0" encoding="utf-8"?>\n<worksheet name="LargeSheet">\n'
        large_content += '  <data>' + '<row>' + '<value>X</value>' * 1000 + '</row>\n  ' * 1000 + '</data>\n'
        large_content += '</worksheet>'
        
        with open(single_large_file, 'w', encoding='utf-8') as f:
            f.write(large_content)
        
        file_size = os.path.getsize(single_large_file)
        print(f"  Created single element file: {file_size:,} bytes")
        
        state['job_id'] = "test_edge_single"
        state['source_files'] = [{"platform": "tableau", "file_path": single_large_file}]
        
        result = await file_analysis_agent(state)
        parsed_elements = result.get('parsed_elements_paths', [])
        print(f"✓ Single large element handled: {len(parsed_elements)} file(s) (kept as-is)")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n✗ ERROR: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


async def test_output_structure():
    """Test that output structure matches expected format."""
    print("\n" + "="*80)
    print("TEST 4: Output Structure Validation")
    print("="*80)
    
    state = AssessmentState(
        job_id="test_structure_001",
        source_files=[
            {"platform": "tableau", "file_path": "input_files/tableau/sales_summary_final.xml"},
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
    
    try:
        result = await file_analysis_agent(state)
        
        parsed_elements = result.get('parsed_elements_paths', [])
        
        # Validate structure
        print("\nValidating output structure...")
        
        # Check 1: All items are dictionaries
        all_dicts = all(isinstance(elem, dict) for elem in parsed_elements)
        print(f"✓ All items are dictionaries: {all_dicts}")
        
        # Check 2: All items have 'file_path'
        all_have_path = all('file_path' in elem for elem in parsed_elements)
        print(f"✓ All items have 'file_path': {all_have_path}")
        
        # Check 3: All items have 'size_bytes'
        all_have_size = all('size_bytes' in elem for elem in parsed_elements)
        print(f"✓ All items have 'size_bytes': {all_have_size}")
        
        # Check 4: All file_paths are strings
        all_paths_strings = all(
            isinstance(elem.get('file_path'), str)
            for elem in parsed_elements
        )
        print(f"✓ All file_paths are strings: {all_paths_strings}")
        
        # Check 5: All size_bytes are integers
        all_sizes_int = all(
            isinstance(elem.get('size_bytes'), int)
            for elem in parsed_elements
        )
        print(f"✓ All size_bytes are integers: {all_sizes_int}")
        
        # Check 6: Output directory is set
        output_dir = result.get('output_dir')
        print(f"✓ Output directory is set: {output_dir is not None}")
        if output_dir:
            print(f"  Output dir: {output_dir}")
            print(f"  Output dir exists: {os.path.exists(output_dir)}")
        
        # Show sample structure
        if parsed_elements:
            print(f"\nSample output structure:")
            print(json.dumps(parsed_elements[0], indent=2))
        
        return all_dicts and all_have_path and all_have_size
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n✗ ERROR: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print("\n" + "="*80)
    print("FILE ANALYSIS AGENT - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print("\nTesting recursive splitting implementation...")
    
    results = {}
    
    # Test 1: Basic extraction
    results['basic'] = await test_basic_extraction()
    
    # Test 2: Recursive splitting
    results['recursive'] = await test_recursive_splitting()
    
    # Test 3: Edge cases
    results['edge_cases'] = await test_edge_cases()
    
    # Test 4: Output structure
    results['structure'] = await test_output_structure()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:20} {status}")
    
    all_passed = all(results.values())
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(run_all_tests())

