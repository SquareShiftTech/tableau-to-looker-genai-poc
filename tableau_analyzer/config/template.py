"""
Feature Template - Defines WHAT features to extract from Tableau components

This file is version-controlled and defines the complete set of features
that will be extracted for complexity analysis and migration assessment.

Agent 2 (Schema Designer) uses these templates to determine HOW to extract each feature.
Agent 3 (Data Extractor) extracts the actual values based on the schema.
"""

# Dashboard Component Features (16 total)
DASHBOARD_FEATURES = [
    # Basic Features
    "dashboard_name",
    "dashboard_id",
    
    # Layout Complexity
    "container_count",
    "custom_container_count",
    
    # Filters
    "simple_filter_count",
    "complex_filter_count",
    "total_filter_count",
    
    # Interactivity/Actions
    "filter_action_count",
    "highlight_action_count",
    "url_action_count",
    "parameter_action_count",
    "set_action_count",
    "total_action_count",
    
    # Parameters
    "parameter_count",
    "parameter_names",
    
    # Relationships
    "worksheets_used",
    "worksheet_count"
]

# Worksheet Component Features (28 total)
WORKSHEET_FEATURES = [
    # Basic Features
    "worksheet_name",
    "worksheet_id",
    "datasource_name",
    
    # Chart Type Detection
    "explicit_chart_type",
    "mark_type",
    "has_dual_axis",
    "axis_count",
    "inferred_chart_type",
    
    # Crosstab/Table Specifics
    "is_crosstab",
    "row_dimension_levels",
    "column_dimension_levels",
    "has_subtotals",
    "has_grand_totals",
    "conditional_formatting_rule_count",
    
    # Hierarchy/Drill-down
    "has_drill_down",
    "drill_levels",
    "hierarchy_type",
    
    # Multi-dimensional Grouping
    "row_dimension_count",
    "column_dimension_count",
    "grouping_depth",
    
    # Fields and Filters
    "field_count",
    "field_names",
    "filter_count",
    "filter_names",
    
    # Visual Complexity
    "has_color_encoding",
    "color_field_count",
    "has_size_encoding",
    "has_reference_lines",
    "reference_line_count",
    "has_reference_bands",
    "has_custom_formatting",
    
    # Relationships
    "calculations_used",
    "calculation_count",
    "datasources_used"
]

# Datasource Component Features (13 total)
DATASOURCE_FEATURES = [
    # Basic Features
    "datasource_name",
    "datasource_id",
    
    # Connection
    "connection_type",
    "database_type",
    
    # Structure
    "table_count",
    "table_names",
    "dimension_count",
    "measure_count",
    
    # Complexity Indicators
    "has_custom_sql",
    "has_data_blending",
    "join_count",
    "join_types",
    "has_relationships"
]

# Calculation Component Features (14 total)
CALCULATION_FEATURES = [
    # Basic Features
    "calculation_name",
    "calculation_id",
    "datasource_name",
    
    # Formula
    "formula",
    "formula_length",
    
    # Complexity Classification
    "complexity_level",
    
    # Specific Features
    "has_lod",
    "lod_type",
    "has_table_calculation",
    "table_calc_type",
    "has_nested_calculations",
    "nesting_level",
    "has_script",
    
    # Relationships
    "used_in_worksheets"
]

# Feature Type Mapping (for Agent 2 to infer types)
FEATURE_TYPES = {
    # String types
    "dashboard_name": "string",
    "dashboard_id": "string",
    "worksheet_name": "string",
    "worksheet_id": "string",
    "datasource_name": "string",
    "datasource_id": "string",
    "calculation_name": "string",
    "calculation_id": "string",
    "explicit_chart_type": "string",
    "mark_type": "string",
    "inferred_chart_type": "string",
    "hierarchy_type": "string",
    "connection_type": "string",
    "database_type": "string",
    "formula": "string",
    "complexity_level": "string",
    "lod_type": "string",
    "table_calc_type": "string",
    
    # Number types
    "container_count": "number",
    "custom_container_count": "number",
    "simple_filter_count": "number",
    "complex_filter_count": "number",
    "total_filter_count": "number",
    "filter_action_count": "number",
    "highlight_action_count": "number",
    "url_action_count": "number",
    "parameter_action_count": "number",
    "set_action_count": "number",
    "total_action_count": "number",
    "parameter_count": "number",
    "worksheet_count": "number",
    "axis_count": "number",
    "row_dimension_levels": "number",
    "column_dimension_levels": "number",
    "conditional_formatting_rule_count": "number",
    "drill_levels": "number",
    "row_dimension_count": "number",
    "column_dimension_count": "number",
    "grouping_depth": "number",
    "field_count": "number",
    "filter_count": "number",
    "color_field_count": "number",
    "reference_line_count": "number",
    "calculation_count": "number",
    "table_count": "number",
    "dimension_count": "number",
    "measure_count": "number",
    "join_count": "number",
    "formula_length": "number",
    "nesting_level": "number",
    
    # Boolean types
    "has_dual_axis": "boolean",
    "is_crosstab": "boolean",
    "has_subtotals": "boolean",
    "has_grand_totals": "boolean",
    "has_drill_down": "boolean",
    "has_color_encoding": "boolean",
    "has_size_encoding": "boolean",
    "has_reference_lines": "boolean",
    "has_reference_bands": "boolean",
    "has_custom_formatting": "boolean",
    "has_custom_sql": "boolean",
    "has_data_blending": "boolean",
    "has_relationships": "boolean",
    "has_lod": "boolean",
    "has_table_calculation": "boolean",
    "has_nested_calculations": "boolean",
    "has_script": "boolean",
    
    # List types
    "parameter_names": "list",
    "worksheets_used": "list",
    "field_names": "list",
    "filter_names": "list",
    "calculations_used": "list",
    "datasources_used": "list",
    "table_names": "list",
    "join_types": "list",
    "used_in_worksheets": "list"
}


def get_feature_type(feature_name: str) -> str:
    """
    Get the expected data type for a feature
    
    Args:
        feature_name: Name of the feature
        
    Returns:
        Data type: "string", "number", "boolean", or "list"
    """
    return FEATURE_TYPES.get(feature_name, "string")
