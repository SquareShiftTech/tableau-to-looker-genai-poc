"""Test script to troubleshoot XML instruction parser."""
import json
import os
import xml.etree.ElementTree as ET
from utils.xml_utils import _parse_instruction, _execute_instruction, extract_features_from_xml
from utils.logger import logger


def find_component(root: ET.Element, component_id: str) -> ET.Element:
    """Find component element by ID or name."""
    clean_id = component_id.strip('{}')
    
    # For dashboards file, look for <dashboard> element directly
    dashboard_elem = root.find('.//dashboard')
    if dashboard_elem is not None:
        return dashboard_elem
    
    # For worksheets file, try to find by name/id
    for worksheet in root.findall('.//worksheet'):
        ws_name = worksheet.get('name', '')
        ws_id = worksheet.get('id', '')
        if component_id in ws_name or component_id in ws_id or ws_name in component_id:
            return worksheet
    
    # For datasources, look for datasource element
    datasource_elem = root.find('.//datasource')
    if datasource_elem is not None:
        return datasource_elem
    
    # Fallback: try to find by ID/name in all elements
    for elem in root.iter():
        elem_id = elem.get('id', '')
        elem_name = elem.get('name', '')
        
        if elem_id:
            if component_id == elem_id or clean_id in elem_id or elem_id in component_id:
                return elem
        
        if elem_name:
            if component_id in elem_name or elem_name in component_id:
                return elem
    
    return root


def test_single_instruction(
    instruction: str,
    xml_file: str,
    component_id: str,
    feature_name: str = ""
) -> dict:
    """Test one instruction and show detailed results."""
    print("\n" + "="*80)
    print(f"TESTING: {feature_name}")
    print("="*80)
    print(f"Instruction: {instruction}")
    
    # 1. Parse instruction
    parsed = _parse_instruction(instruction)
    print(f"\n[PARSING]")
    print(f"  Pattern matched: {parsed['pattern']}")
    print(f"  Query: {parsed.get('query', 'N/A')}")
    print(f"  Attributes: {parsed.get('attributes', [])}")
    print(f"  Attribute (single): {parsed.get('attribute', 'N/A')}")
    print(f"  Conditions: {parsed.get('conditions', {})}")
    print(f"  Exclusions: {parsed.get('exclusions', [])}")
    print(f"  Path: {parsed.get('path', 'N/A')}")
    
    if parsed['pattern'] == 'generic':
        print(f"  [WARNING] Pattern not matched, using generic fallback")
    
    # 2. Load XML and find component
    if not os.path.exists(xml_file):
        print(f"\n[ERROR] XML file not found: {xml_file}")
        return {'success': False, 'error': 'File not found'}
    
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        component_elem = find_component(root, component_id)
        print(f"\n[XML]")
        print(f"  Component element tag: {component_elem.tag}")
        print(f"  Component element ID: {component_elem.get('id', 'N/A')}")
        print(f"  Component element name: {component_elem.get('name', 'N/A')}")
    except Exception as e:
        print(f"\n[ERROR] Failed to parse XML: {e}")
        return {'success': False, 'error': str(e)}
    
    # 3. Execute instruction
    try:
        result = _execute_instruction(component_elem, parsed)
        print(f"\n[RESULT]")
        print(f"  Result: {result}")
        print(f"  Result type: {type(result).__name__}")
        print(f"  Result is None: {result is None}")
        print(f"  Result is empty: {result == [] or result == {}}")
        
        if result is None:
            print(f"  [FAILED] Result is None")
        elif result == [] or result == {}:
            print(f"  [WARNING] Result is empty")
        else:
            print(f"  [SUCCESS] Result extracted")
        
        return {
            'success': result is not None and result != [] and result != {},
            'pattern': parsed['pattern'],
            'result': result,
            'result_type': type(result).__name__
        }
    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def test_all_instructions_from_discovered():
    """Test all instructions from discovered_components.json."""
    discovered_file = "output/test_parsing_20251216_112457/discovered_components.json"
    
    if not os.path.exists(discovered_file):
        print(f"Error: {discovered_file} not found")
        return
    
    with open(discovered_file, 'r', encoding='utf-8') as f:
        discovered = json.load(f)
    
    components = discovered.get('components', {})
    
    # Test dashboard instructions first
    dashboards = components.get('dashboards', [])
    if dashboards:
        dashboard = dashboards[0]
        dashboard_id = dashboard.get('id', '')
        dashboard_file = dashboard.get('file', '')
        instructions = dashboard.get('parsing_instructions', {})
        
        print("\n" + "="*80)
        print("TESTING DASHBOARD INSTRUCTIONS")
        print("="*80)
        print(f"Dashboard: {dashboard.get('name')}")
        print(f"ID: {dashboard_id}")
        print(f"File: {dashboard_file}")
        
        results = {}
        for feature_name, instruction in instructions.items():
            result = test_single_instruction(
                instruction,
                dashboard_file,
                dashboard_id,
                feature_name
            )
            results[feature_name] = result
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        success_count = sum(1 for r in results.values() if r.get('success'))
        total_count = len(results)
        print(f"Success: {success_count}/{total_count} ({success_count*100//total_count}%)")
        
        print("\nFailed features:")
        for feature_name, result in results.items():
            if not result.get('success'):
                print(f"  [FAILED] {feature_name}: {result.get('pattern', 'unknown')} - {result.get('error', 'No result')}")
        
        print("\nSuccessful features:")
        for feature_name, result in results.items():
            if result.get('success'):
                print(f"  [SUCCESS] {feature_name}: {result.get('pattern')} - {result.get('result_type')}")


def test_extract_features_from_xml():
    """Test extract_features_from_xml function (full workflow as used by parsing agent)."""
    discovered_file = "output/test_parsing_20251216_112457/discovered_components.json"
    
    if not os.path.exists(discovered_file):
        print(f"Error: {discovered_file} not found")
        return
    
    with open(discovered_file, 'r', encoding='utf-8') as f:
        discovered = json.load(f)
    
    components = discovered.get('components', {})
    
    # Test dashboard extraction
    dashboards = components.get('dashboards', [])
    if dashboards:
        dashboard = dashboards[0]
        dashboard_id = dashboard.get('id', '')
        dashboard_file = dashboard.get('file', '')
        parsing_instructions = dashboard.get('parsing_instructions', {})
        
        print("\n" + "="*80)
        print("TESTING FULL WORKFLOW: extract_features_from_xml")
        print("="*80)
        print(f"Dashboard: {dashboard.get('name')}")
        print(f"ID: {dashboard_id}")
        print(f"File: {dashboard_file}")
        print(f"Features to extract: {list(parsing_instructions.keys())}")
        
        # Call extract_features_from_xml (same as parsing agent)
        features = extract_features_from_xml(
            dashboard_file,
            dashboard_id,
            parsing_instructions,
            None  # feature_catalog
        )
        
        print("\n" + "="*80)
        print("EXTRACTION RESULTS")
        print("="*80)
        
        success_count = 0
        null_count = 0
        failed_features = []
        
        for feature_name, value in features.items():
            if value is None:
                null_count += 1
                failed_features.append(feature_name)
                print(f"  [FAILED] {feature_name}: None")
            elif value == [] or value == {}:
                print(f"  [WARNING] {feature_name}: Empty ({type(value).__name__})")
            else:
                success_count += 1
                print(f"  [SUCCESS] {feature_name}: {type(value).__name__} - {str(value)[:100]}...")
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        total_count = len(features)
        print(f"Total features: {total_count}")
        print(f"Success: {success_count}/{total_count} ({success_count*100//total_count if total_count > 0 else 0}%)")
        print(f"Null values: {null_count}")
        print(f"Empty values: {total_count - success_count - null_count}")
        
        if failed_features:
            print(f"\nFailed features: {failed_features}")
        
        return features, failed_features


if __name__ == "__main__":
    # Test individual instructions
    test_all_instructions_from_discovered()
    
    # Test full workflow
    print("\n\n")
    test_extract_features_from_xml()
