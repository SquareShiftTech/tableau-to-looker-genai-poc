"""
Agent 3: Data Extractor (Comprehensive Workflow)

This agent extracts actual feature values based on Agent 2's schema.
Includes per-feature retry logic with query rephrasing.
"""
import sys
import time
import re
import json
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from agents.agent_1 import query_tableau_expert
from config.settings import MAX_RETRIES_AGENT_3_PER_FEATURE, RETRY_DELAY_SECONDS, MIN_FEATURES_EXTRACTED_PERCENT


def agent_3_data_extractor(state: AnalysisState) -> AnalysisState:
    """
    Agent 3: Data Extractor with Per-Feature Retry
    
    Extracts all features for all components using Agent 2's schema.
    Includes retry logic for failed extractions.
    
    Args:
        state: Current workflow state (Agent 2 schema must be ready)
        
    Returns:
        Updated state with extracted_features and extraction stats
    """
    print("\n" + "="*70)
    print("📦 AGENT 3: DATA EXTRACTOR (WITH PER-FEATURE RETRY)")
    print("="*70)
    
    # Check prerequisites
    if not state.get("agent_1_ready", False):
        error_msg = "Agent 1 not ready - cannot extract data"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        return state
    
    if "feature_schema" not in state:
        error_msg = "Feature schema not found - cannot extract data"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        return state
    
    print("✅ Agent 1 ready and schema available")
    print(f"🔄 Max Retries per Feature: {MAX_RETRIES_AGENT_3_PER_FEATURE}")
    
    inventory = state.get("inventory", {})
    schema = state["feature_schema"]
    
    extracted_data = {
        "dashboards": [],
        "worksheets": [],
        "datasources": [],
        "calculations": [],
        "relationships": {}
    }
    
    extraction_stats = {
        "features_attempted": 0,
        "features_successful": 0,
        "features_failed": 0,
        "features_retried": 0,
        "components_processed": 0
    }
    
    # Extract Dashboards
    print("\n" + "-"*70)
    print("STEP 1: EXTRACTING DASHBOARD DATA")
    print("-"*70)
    for dashboard in inventory.get("dashboards", []):
        dashboard_data = extract_component_features(
            component_type="dashboard",
            component=dashboard,
            schema=schema["dashboard"],
            state=state,
            extraction_stats=extraction_stats
        )
        extracted_data["dashboards"].append(dashboard_data)
        extraction_stats["components_processed"] += 1
        print(f"   ✓ {dashboard_data.get('dashboard_name', 'Unknown')}")
    
    # Extract Worksheets
    print("\n" + "-"*70)
    print("STEP 2: EXTRACTING WORKSHEET DATA")
    print("-"*70)
    for worksheet in inventory.get("worksheets", []):
        worksheet_data = extract_component_features(
            component_type="worksheet",
            component=worksheet,
            schema=schema["worksheet"],
            state=state,
            extraction_stats=extraction_stats
        )
        extracted_data["worksheets"].append(worksheet_data)
        extraction_stats["components_processed"] += 1
        print(f"   ✓ {worksheet_data.get('worksheet_name', 'Unknown')}")
    
    # Extract Datasources
    print("\n" + "-"*70)
    print("STEP 3: EXTRACTING DATASOURCE DATA")
    print("-"*70)
    for datasource in inventory.get("datasources", []):
        datasource_data = extract_component_features(
            component_type="datasource",
            component=datasource,
            schema=schema["datasource"],
            state=state,
            extraction_stats=extraction_stats
        )
        extracted_data["datasources"].append(datasource_data)
        extraction_stats["components_processed"] += 1
        print(f"   ✓ {datasource_data.get('datasource_name', 'Unknown')}")
    
    # Extract Calculations
    print("\n" + "-"*70)
    print("STEP 4: EXTRACTING CALCULATION DATA")
    print("-"*70)
    for calculation in inventory.get("calculations", []):
        calculation_data = extract_component_features(
            component_type="calculation",
            component=calculation,
            schema=schema["calculation"],
            state=state,
            extraction_stats=extraction_stats
        )
        extracted_data["calculations"].append(calculation_data)
        extraction_stats["components_processed"] += 1
        print(f"   ✓ {calculation_data.get('calculation_name', 'Unknown')}")
    
    # Build Relationships
    print("\n" + "-"*70)
    print("STEP 5: BUILDING RELATIONSHIPS")
    print("-"*70)
    extracted_data["relationships"] = build_relationships(extracted_data)
    print("✅ Relationships mapped")
    
    # Store results
    state["extracted_features"] = extracted_data
    state["features_attempted"] = extraction_stats["features_attempted"]
    state["features_successful"] = extraction_stats["features_successful"]
    state["features_failed"] = extraction_stats["features_failed"]
    state["agent_3_retry_count"] = extraction_stats["features_retried"]
    
    # Print summary
    print_extraction_summary(extracted_data, extraction_stats)
    
    print("\n" + "="*70)
    print("✅ AGENT 3: DATA EXTRACTION COMPLETE")
    print("="*70)
    
    return state


def extract_component_features(
    component_type: str,
    component: Dict[str, Any],
    schema: Dict[str, Any],
    state: AnalysisState,
    extraction_stats: Dict[str, int]
) -> Dict[str, Any]:
    """
    Extract all features for a single component with per-feature retry
    
    Args:
        component_type: Type of component
        component: Component data from inventory
        schema: Extraction schema for this component type
        state: Current workflow state
        extraction_stats: Statistics dict to update
        
    Returns:
        Dict with all extracted features
    """
    extracted = {}
    component_name = component.get("name") or component.get("@name", "Unknown")
    
    for feature_name, extraction_info in schema.items():
        extraction_stats["features_attempted"] += 1
        
        # Retry loop for this feature
        for attempt in range(1, MAX_RETRIES_AGENT_3_PER_FEATURE + 1):
            try:
                if extraction_info["method"] == "direct":
                    # Read directly from inventory/component
                    value = extract_direct_value(component, feature_name, extraction_info["type"])
                    extracted[feature_name] = value
                    extraction_stats["features_successful"] += 1
                    break  # Success!
                
                elif extraction_info["method"] == "query":
                    # Query Agent 1
                    query = extraction_info["query_template"].format(
                        name=component_name,
                        component_type=component_type
                    )
                    
                    # Adjust query on retries
                    if attempt > 1:
                        query = rephrase_query(query, attempt)
                        extraction_stats["features_retried"] += 1
                    
                    answer = query_tableau_expert(state, query, "agent_3_extractor")
                    
                    # Parse answer to correct type
                    value = parse_agent_answer(answer, extraction_info["type"], feature_name)
                    
                    # Validate extracted value
                    if validate_extracted_value(value, extraction_info["type"]):
                        extracted[feature_name] = value
                        extraction_stats["features_successful"] += 1
                        break  # Success!
                    else:
                        if attempt < MAX_RETRIES_AGENT_3_PER_FEATURE:
                            time.sleep(0.5)  # Short delay between feature retries
                        
            except Exception as e:
                if attempt == MAX_RETRIES_AGENT_3_PER_FEATURE:
                    # Final attempt failed, use default
                    extracted[feature_name] = get_default_value(extraction_info["type"])
                    extraction_stats["features_failed"] += 1
                else:
                    time.sleep(0.5)
    
    return extracted


def extract_direct_value(component: Dict[str, Any], feature_name: str, expected_type: str) -> Any:
    """
    Extract value directly from component data
    
    Args:
        component: Component dict
        feature_name: Name of feature
        expected_type: Expected data type
        
    Returns:
        Extracted value or default
    """
    # Try direct key
    if feature_name in component:
        return component[feature_name]
    
    # Try in attributes
    if "attributes" in component and feature_name in component["attributes"]:
        return component["attributes"][feature_name]
    
    # Return default
    return get_default_value(expected_type)


def parse_agent_answer(answer: str, expected_type: str, feature_name: str) -> Any:
    """
    Parse Agent 1's text answer into the expected data type
    
    Args:
        answer: Text response from Agent 1
        expected_type: "string", "number", "boolean", "list"
        feature_name: Name of feature being extracted
        
    Returns:
        Parsed value in correct type
    """
    try:
        if expected_type == "number":
            # Extract number from text
            numbers = re.findall(r'\d+', answer)
            return int(numbers[0]) if numbers else 0
        
        elif expected_type == "boolean":
            # Check for yes/no, true/false
            answer_lower = answer.lower()
            if any(word in answer_lower for word in ["yes", "true", "does", "has"]):
                if not any(word in answer_lower for word in ["no", "not", "doesn't", "hasn't"]):
                    return True
            return False
        
        elif expected_type == "list":
            # Try to extract list items
            if "[" in answer and "]" in answer:
                try:
                    list_str = answer[answer.find("["):answer.rfind("]")+1]
                    return json.loads(list_str)
                except:
                    pass
            
            # Try comma-separated
            if "," in answer:
                items = [item.strip() for item in answer.split(",")]
                return [item for item in items if item]
            
            # Single item
            if answer and len(answer) < 100:
                return [answer.strip()]
            
            return []
        
        else:  # string
            return answer.strip()
    
    except Exception as e:
        return get_default_value(expected_type)


def rephrase_query(query: str, attempt: int) -> str:
    """
    Rephrase query for retry attempts
    
    Args:
        query: Original query
        attempt: Attempt number (2 or 3)
        
    Returns:
        Rephrased query
    """
    if attempt == 2:
        # Try with different wording
        query = query.replace("How many", "Count the")
        query = query.replace("What is", "Tell me")
        query = query.replace("Does", "Check if")
    elif attempt == 3:
        # Simplify to yes/no or simple count
        if "how many" in query.lower():
            query = query.replace("?", " and give me the count?")
        else:
            query = query + " Answer with just yes or no."
    
    return query


def validate_extracted_value(value: Any, expected_type: str) -> bool:
    """
    Validate that extracted value is reasonable
    
    Args:
        value: Extracted value
        expected_type: Expected type
        
    Returns:
        True if valid
    """
    if value is None:
        return False
    
    if expected_type == "number":
        return isinstance(value, (int, float)) and value >= 0
    elif expected_type == "boolean":
        return isinstance(value, bool)
    elif expected_type == "list":
        return isinstance(value, list)
    elif expected_type == "string":
        return isinstance(value, str) and len(value) > 0
    
    return True


def get_default_value(data_type: str) -> Any:
    """
    Return default value for a data type
    
    Args:
        data_type: Type name
        
    Returns:
        Default value
    """
    defaults = {
        "string": "",
        "number": 0,
        "boolean": False,
        "list": []
    }
    return defaults.get(data_type, None)


def build_relationships(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build relationship mappings between components
    
    Args:
        extracted_data: Extracted data for all components
        
    Returns:
        Dict with relationship mappings
    """
    relationships = {
        "dashboard_to_worksheets": {},
        "worksheet_to_datasources": {},
        "worksheet_to_calculations": {},
        "calculation_to_datasource": {},
        "dashboard_actions": {}
    }
    
    # Dashboard → Worksheets
    for dashboard in extracted_data.get("dashboards", []):
        name = dashboard.get("dashboard_name")
        worksheets = dashboard.get("worksheets_used", [])
        if name and worksheets:
            relationships["dashboard_to_worksheets"][name] = worksheets
    
    # Worksheet → Datasources
    for worksheet in extracted_data.get("worksheets", []):
        name = worksheet.get("worksheet_name")
        datasources = worksheet.get("datasources_used", [])
        if name:
            if isinstance(datasources, list):
                relationships["worksheet_to_datasources"][name] = datasources
            else:
                # Single datasource
                ds = worksheet.get("datasource_name")
                if ds:
                    relationships["worksheet_to_datasources"][name] = [ds]
    
    # Worksheet → Calculations
    for worksheet in extracted_data.get("worksheets", []):
        name = worksheet.get("worksheet_name")
        calcs = worksheet.get("calculations_used", [])
        if name and calcs:
            relationships["worksheet_to_calculations"][name] = calcs
    
    # Calculation → Datasource
    for calc in extracted_data.get("calculations", []):
        name = calc.get("calculation_name")
        datasource = calc.get("datasource_name")
        if name and datasource:
            relationships["calculation_to_datasource"][name] = datasource
    
    return relationships


def print_extraction_summary(extracted_data: Dict[str, Any], stats: Dict[str, int]) -> None:
    """
    Print summary of data extraction
    
    Args:
        extracted_data: Extracted data
        stats: Extraction statistics
    """
    print("\n📊 EXTRACTION SUMMARY:")
    print(f"   📦 Components Processed: {stats['components_processed']}")
    print(f"   ✅ Features Successful: {stats['features_successful']}")
    print(f"   🔄 Features Retried: {stats['features_retried']}")
    print(f"   ❌ Features Failed: {stats['features_failed']}")
    print(f"   📊 Total Features Attempted: {stats['features_attempted']}")
    
    if stats['features_attempted'] > 0:
        success_rate = (stats['features_successful'] / stats['features_attempted']) * 100
        print(f"   📈 Success Rate: {success_rate:.1f}%")
    
    print("\n📋 COMPONENTS EXTRACTED:")
    print(f"   • Dashboards: {len(extracted_data.get('dashboards', []))}")
    print(f"   • Worksheets: {len(extracted_data.get('worksheets', []))}")
    print(f"   • Datasources: {len(extracted_data.get('datasources', []))}")
    print(f"   • Calculations: {len(extracted_data.get('calculations', []))}")
