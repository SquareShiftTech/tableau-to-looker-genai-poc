"""
Agent 2: Feature Schema Designer (Comprehensive Workflow)

This agent defines WHAT features to extract and HOW to extract them.
It creates an extraction schema that Agent 3 will follow.
"""
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.state import AnalysisState
from config.template import (
    DASHBOARD_FEATURES,
    WORKSHEET_FEATURES,
    DATASOURCE_FEATURES,
    CALCULATION_FEATURES,
    get_feature_type
)


def agent_2_schema_designer(state: AnalysisState) -> AnalysisState:
    """
    Agent 2: Feature Schema Designer
    
    Loads feature templates (WHAT to extract) and determines extraction
    methods (HOW to extract) for each feature.
    
    Args:
        state: Current workflow state (Agent 1 must be ready)
        
    Returns:
        Updated state with feature_schema
    """
    print("\n" + "="*70)
    print("📋 AGENT 2: FEATURE SCHEMA DESIGNER")
    print("="*70)
    
    # Check if Agent 1 is ready
    if not state.get("agent_1_ready", False):
        error_msg = "Agent 1 not ready - cannot generate schema"
        print(f"❌ {error_msg}")
        state["errors"].append(error_msg)
        return state
    
    print("✅ Agent 1 is ready - generating extraction schema")
    
    inventory = state.get("inventory", {})
    
    print("\n📋 Loaded feature templates:")
    print(f"   • Dashboard features: {len(DASHBOARD_FEATURES)}")
    print(f"   • Worksheet features: {len(WORKSHEET_FEATURES)}")
    print(f"   • Datasource features: {len(DATASOURCE_FEATURES)}")
    print(f"   • Calculation features: {len(CALCULATION_FEATURES)}")
    
    print("\n" + "-"*70)
    print("STEP 1: GENERATING EXTRACTION SCHEMA")
    print("-"*70)
    
    # Generate extraction schema for each component type
    schema = {
        "dashboard": generate_component_schema("dashboard", DASHBOARD_FEATURES, inventory),
        "worksheet": generate_component_schema("worksheet", WORKSHEET_FEATURES, inventory),
        "datasource": generate_component_schema("datasource", DATASOURCE_FEATURES, inventory),
        "calculation": generate_component_schema("calculation", CALCULATION_FEATURES, inventory)
    }
    
    state["feature_schema"] = schema
    
    # Print schema statistics
    print_schema_statistics(schema)
    
    print("\n" + "="*70)
    print("✅ AGENT 2: SCHEMA GENERATION COMPLETE")
    print("="*70)
    
    return state


def generate_component_schema(component_type: str, features: List[str], inventory: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate extraction schema for a component type
    
    For each feature, determines:
    - Data type
    - Extraction method (direct from inventory or query Agent 1)
    - Query template (if query method)
    
    Args:
        component_type: "dashboard", "worksheet", "datasource", or "calculation"
        features: List of feature names to extract
        inventory: Inventory from Agent 1
        
    Returns:
        Schema dict mapping feature_name → extraction info
    """
    schema = {}
    
    # Get sample component to check what's available in inventory
    sample = get_sample_component(component_type, inventory)
    
    for feature in features:
        feature_type = get_feature_type(feature)
        
        # Check if feature exists in inventory already
        if sample and feature_exists_in_inventory(feature, sample):
            schema[feature] = {
                "type": feature_type,
                "method": "direct",
                "source": "inventory"
            }
        else:
            # Need to query Agent 1
            schema[feature] = {
                "type": feature_type,
                "method": "query",
                "source": "agent_1",
                "query_template": generate_query_template(component_type, feature)
            }
    
    return schema


def get_sample_component(component_type: str, inventory: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a sample component from inventory to check available fields
    
    Args:
        component_type: Type of component
        inventory: Inventory dict
        
    Returns:
        Sample component dict or empty dict
    """
    plural_map = {
        "dashboard": "dashboards",
        "worksheet": "worksheets",
        "datasource": "datasources",
        "calculation": "calculations"
    }
    
    plural = plural_map.get(component_type, component_type + "s")
    components = inventory.get(plural, [])
    
    return components[0] if components else {}


def feature_exists_in_inventory(feature: str, component: Dict[str, Any]) -> bool:
    """
    Check if a feature exists in the inventory component
    
    Args:
        feature: Feature name
        component: Component dict
        
    Returns:
        True if feature exists
    """
    # Check direct key
    if feature in component:
        return True
    
    # Check in attributes
    if "attributes" in component and feature in component["attributes"]:
        return True
    
    return False


def generate_query_template(component_type: str, feature: str) -> str:
    """
    Generate appropriate query template for Agent 1
    
    Args:
        component_type: Type of component
        feature: Feature name
        
    Returns:
        Query template string with {name} placeholder
    """
    # Specific query templates for common features
    query_templates = {
        # Dashboard queries
        "container_count": "How many containers are in dashboard '{name}'?",
        "total_filter_count": "How many filters are on dashboard '{name}'?",
        "total_action_count": "How many actions exist on dashboard '{name}'?",
        "parameter_count": "How many parameters does dashboard '{name}' have?",
        "parameter_names": "What are the names of parameters in dashboard '{name}'?",
        "worksheets_used": "Which worksheets are used in dashboard '{name}'?",
        
        # Worksheet queries
        "explicit_chart_type": "What is the chart type of worksheet '{name}'?",
        "mark_type": "What is the mark type used in worksheet '{name}'?",
        "has_dual_axis": "Does worksheet '{name}' have dual axis?",
        "field_count": "How many fields does worksheet '{name}' have?",
        "field_names": "What are the field names in worksheet '{name}'?",
        "filter_count": "How many filters does worksheet '{name}' have?",
        "has_color_encoding": "Does worksheet '{name}' use color encoding?",
        "calculations_used": "What calculations are used in worksheet '{name}'?",
        
        # Datasource queries
        "connection_type": "What is the connection type of datasource '{name}'?",
        "database_type": "What is the database type of datasource '{name}'?",
        "table_count": "How many tables are in datasource '{name}'?",
        "table_names": "What tables are in datasource '{name}'?",
        "has_custom_sql": "Does datasource '{name}' have custom SQL?",
        "join_count": "How many joins are in datasource '{name}'?",
        
        # Calculation queries
        "formula": "What is the formula for calculation '{name}'?",
        "has_lod": "Does calculation '{name}' use LOD expressions?",
        "lod_type": "What type of LOD expression does calculation '{name}' use (FIXED, INCLUDE, or EXCLUDE)?",
        "has_table_calculation": "Does calculation '{name}' use table calculations?",
        "has_nested_calculations": "Does calculation '{name}' reference other calculations?"
    }
    
    # Return specific template or generic one
    if feature in query_templates:
        return query_templates[feature]
    else:
        # Generic template
        return f"What is the {feature.replace('_', ' ')} of {component_type} '{{name}}'?"


def print_schema_statistics(schema: Dict[str, Any]) -> None:
    """
    Print statistics about the generated schema
    
    Args:
        schema: Complete extraction schema
    """
    print("\n📊 SCHEMA STATISTICS:")
    
    for component_type, component_schema in schema.items():
        total = len(component_schema)
        direct = sum(1 for f in component_schema.values() if f["method"] == "direct")
        query = sum(1 for f in component_schema.values() if f["method"] == "query")
        
        print(f"\n   {component_type.upper()}:")
        print(f"      Total features: {total}")
        print(f"      Direct from inventory: {direct}")
        print(f"      Query Agent 1: {query}")
