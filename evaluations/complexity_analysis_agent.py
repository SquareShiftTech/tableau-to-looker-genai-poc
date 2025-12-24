"""
Complexity Analysis Agent
Analyzes Tableau features from PostgreSQL and outputs per-instance complexity assessments.
Uses hybrid approach: rule-based for standard cases, LLM for edge cases.
"""

import json
import re
from typing import TypedDict, Annotated, Dict, Any, List, Optional
import operator

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from langchain_google_vertexai import ChatVertexAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from config.complexity_rules import load_complexity_rules
from complexity_prompts import (
    build_visualization_prompt,
    build_calculated_field_prompt,
    build_dashboard_prompt,
    build_generic_complexity_prompt
)


# ============================================================================
# CONFIG
# ============================================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "tableau_migration",
    "user": "postgres",
    "password": "postgres"
}

DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

llm = ChatVertexAI(model="gemini-2.0-flash-001", temperature=0)


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_db_connection():
    """Get PostgreSQL database connection."""
    return psycopg2.connect(**DB_CONFIG)


def create_sql_agent_helper():
    """Create SQL agent for generating and executing queries with natural language."""
    db = SQLDatabase.from_uri(DATABASE_URL)
    
    agent = create_sql_agent(
        llm=llm,
        db=db,
        verbose=False,
        handle_parsing_errors=True,
        prefix="""You are a Tableau migration assessment agent. You help query the Tableau metadata stored in PostgreSQL.

Available tables:
- workbooks (id, name, version, site, project_path)
- worksheets (id, workbook_id, name, datasource_id, columns_used, rows_used)
- worksheet_elements (id, worksheet_id, pane_id, mark_class, element_type, encoding JSONB, style JSONB)
- fields (id, datasource_id, caption, internal_name, formula, data_type, role, is_calculated)
- datasources (id, workbook_id, name, caption, connection_type, db_name, db_schema, is_extract)
- dashboards (id, workbook_id, name, width, height, zones JSONB)
- dashboard_components (id, dashboard_id, worksheet_id, component_type, x_pos, y_pos, width, height, is_visible)
- actions (id, workbook_id, name, action_type, source_object_name, target_object_name, logic_details JSONB)

Execute queries and return results. Help understand the Tableau environment for migration planning."""
    )
    
    return agent


def query_with_sql_agent(natural_language_query: str) -> List[Dict[str, Any]]:
    """
    Execute a natural language query using SQL agent and return structured results.
    
    Uses a hybrid approach:
    1. Ask SQL agent to generate SQL query from natural language
    2. Extract SQL from agent's response
    3. Execute SQL directly with RealDictCursor for structured results
    
    Args:
        natural_language_query: Natural language description of the query
        
    Returns:
        List of dictionaries representing query results
    """
    try:
        sql_agent = create_sql_agent_helper()
        
        # Ask the agent to generate the SQL query
        sql_generation_prompt = f"""Generate a PostgreSQL SQL query to answer this request: {natural_language_query}

Return ONLY the SQL query statement, no explanations, no markdown code blocks, just the raw SQL."""
        
        sql_result = sql_agent.invoke({"input": sql_generation_prompt})
        sql_output = sql_result.get("output", "")
        
        # Extract SQL from the output
        sql_query = None
        
        # Try to extract SQL from markdown code blocks
        if "```sql" in sql_output:
            sql_query = sql_output.split("```sql")[1].split("```")[0].strip()
        elif "```" in sql_output:
            # Extract from generic code blocks
            parts = sql_output.split("```")
            for part in parts:
                if "SELECT" in part.upper() or "WITH" in part.upper():
                    sql_query = part.strip()
                    break
        
        # If not in code blocks, try to find SQL in the text
        if not sql_query:
            lines = sql_output.split("\n")
            sql_lines = []
            for line in lines:
                stripped = line.strip()
                # Skip empty lines and comments at the start
                if not stripped or stripped.startswith("--"):
                    continue
                # Start collecting when we see SELECT or WITH
                if "SELECT" in stripped.upper() or "WITH" in stripped.upper() or sql_lines:
                    sql_lines.append(line)
                    # Stop at semicolon or when we have a complete query
                    if stripped.endswith(";") or (len(sql_lines) > 5 and "FROM" in stripped.upper()):
                        break
            
            if sql_lines:
                sql_query = "\n".join(sql_lines).strip().rstrip(";")
        
        # If we still don't have SQL, try to use the natural language query directly
        # by asking the agent to execute it and parse results
        if not sql_query or len(sql_query) < 10:
            # Fallback: execute the natural language query directly with the agent
            # and try to parse the text results (less reliable but works)
            result = sql_agent.invoke({"input": natural_language_query})
            output_text = result.get("output", "")
            
            # Try to parse structured data from text output
            # This is a simple parser - may not work for all cases
            # For now, return empty and let the calling function handle fallback
            print(f"Warning: Could not extract SQL from agent response. Output: {output_text[:200]}")
            return []
        
        # Execute the extracted SQL with RealDictCursor for structured results
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql_query)
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        finally:
            conn.close()
            
    except Exception as e:
        # Log error and return empty list - calling function should handle fallback
        print(f"Warning: SQL agent query failed: {str(e)}")
        return []


# ============================================================================
# COMPLEXITY ANALYSIS TOOLS
# ============================================================================

def determine_visualization_complexity(mark_class: str, encoding: Dict[str, Any], rules: Dict[str, Any]) -> tuple[str, str]:
    """
    Determine visualization complexity using rule-based logic.
    
    Returns:
        Tuple of (complexity_level, reasoning)
    """
    if not mark_class:
        return "low", "No mark class specified"
    
    mark_class_lower = mark_class.lower()
    
    # Check against rules
    for level in ["high", "medium", "low"]:
        level_rules = rules.get(level, {})
        mark_classes = level_rules.get("mark_classes", [])
        if mark_class_lower in [mc.lower() for mc in mark_classes]:
            # Check for dual-axis in encoding
            if encoding and isinstance(encoding, dict):
                # Count axes in encoding
                axis_count = 0
                for key in encoding.keys():
                    if "axis" in key.lower() or "x" in key.lower() or "y" in key.lower():
                        axis_count += 1
                
                if axis_count > 1 and level == "low":
                    return "medium", f"Mark class '{mark_class}' is low complexity, but dual-axis detected"
            
            return level, f"Mark class '{mark_class}' matches {level} complexity rules"
    
    # Default to medium if not found
    return "medium", f"Mark class '{mark_class}' not in rules, defaulting to medium"


def determine_calculated_field_complexity(formula: str, rules: Dict[str, Any]) -> tuple[str, List[str]]:
    """
    Determine calculated field complexity using rule-based logic.
    
    Returns:
        Tuple of (complexity_level, matched_patterns)
    """
    if not formula:
        return "low", []
    
    formula_upper = formula.upper()
    matched_patterns = []
    max_complexity = "low"
    
    # Check against rules (high to low priority)
    for level in ["high", "medium", "low"]:
        level_rules = rules.get(level, {})
        regex_patterns = level_rules.get("regex", [])
        
        for pattern in regex_patterns:
            try:
                if re.search(pattern, formula_upper):
                    matched_patterns.append(f"{level}: {pattern}")
                    # Update max complexity
                    if level == "high":
                        max_complexity = "high"
                    elif level == "medium" and max_complexity != "high":
                        max_complexity = "medium"
            except re.error:
                continue
    
    # Fallback: If formula contains LOD indicators but no patterns matched, classify as medium
    if not matched_patterns:
        # Check for LOD indicators (curly braces indicate LOD expressions)
        if "{" in formula and ("FIXED" in formula_upper or "INCLUDE" in formula_upper or "EXCLUDE" in formula_upper):
            return "medium", ["LOD expression detected but no specific pattern matched"]
        return "low", ["No patterns matched, defaulting to low"]
    
    return max_complexity, matched_patterns


def determine_dashboard_complexity(component_count: int, action_types: List[str], rules: Dict[str, Any]) -> tuple[str, List[str]]:
    """
    Determine dashboard complexity using rule-based logic.
    
    Returns:
        Tuple of (complexity_level, matched_indicators)
    """
    matched_indicators = []
    
    # Check component count
    for level in ["high", "medium", "low"]:
        level_rules = rules.get(level, {})
        min_count = level_rules.get("component_count_min", 0)
        max_count = level_rules.get("component_count_max", float('inf'))
        
        if min_count <= component_count <= max_count:
            matched_indicators.append(f"{level}: component_count={component_count}")
            complexity = level
            break
    else:
        # Default based on count
        if component_count >= 6:
            complexity = "high"
            matched_indicators.append("high: component_count>=6")
        elif component_count >= 2:
            complexity = "medium"
            matched_indicators.append("medium: component_count>=2")
        else:
            complexity = "low"
            matched_indicators.append("low: component_count<=1")
    
    # Check action types
    action_rules = rules.get("actions", {})
    for action_type in action_types:
        for level in ["high", "medium", "low"]:
            level_action_types = action_rules.get(level, {}).get("action_types", [])
            if action_type.lower() in [at.lower() for at in level_action_types]:
                if level == "high" and complexity != "high":
                    complexity = "high"
                    matched_indicators.append(f"high: action_type={action_type}")
                elif level == "medium" and complexity == "low":
                    complexity = "medium"
                    matched_indicators.append(f"medium: action_type={action_type}")
                break
    
    return complexity, matched_indicators


@tool
def analyze_visualization_complexity() -> str:
    """
    Analyze visualization complexity from worksheet_elements.
    Uses SQL agent to execute query dynamically with natural language.
    Returns JSON string with per-instance complexity analysis.
    """
    rules = load_complexity_rules("tableau").get("visualizations", {})
    results = []
    
    # Natural language query for SQL agent
    # Note: dashboard_components.worksheet_id may be NULL if worksheet name doesn't match dashboard zone @param
    # This is expected - worksheets may exist without being used in dashboards
    natural_language_query = """Get all worksheet elements with their mark_class, worksheet name, workbook name, dashboard names (as an array), and encoding. Include all dashboards that use each worksheet. Only include worksheet elements where mark_class is not null."""
    
    # Use SQL agent to execute query and get structured results
    rows = query_with_sql_agent(natural_language_query)
    
    # Fallback to direct query if SQL agent fails
    # Note: dashboard_names will be empty [] if:
    # 1. Worksheet is not used in any dashboard (dashboard_components.worksheet_id is NULL)
    # 2. Worksheet name doesn't match dashboard zone @param during ingestion
    if not rows:
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT
                      we.mark_class,
                      wks.name as worksheet_name,
                      wb.name as workbook_name,
                      ARRAY_AGG(DISTINCT d.name) FILTER (WHERE d.name IS NOT NULL) as dashboard_names,
                      we.encoding
                    FROM worksheet_elements we
                    JOIN worksheets wks ON we.worksheet_id = wks.id
                    JOIN workbooks wb ON wks.workbook_id = wb.id
                    LEFT JOIN dashboard_components dc ON dc.worksheet_id = wks.id
                    LEFT JOIN dashboards d ON dc.dashboard_id = d.id
                    WHERE we.mark_class IS NOT NULL
                    GROUP BY we.mark_class, wks.name, wb.name, we.encoding
                """)
                rows = cur.fetchall()
        finally:
            conn.close()
    
    # Process results
    for row in rows:
        mark_class = row.get("mark_class", "")
        encoding = row.get("encoding") or {}
        worksheet_name = row.get("worksheet_name", "")
        workbook_name = row.get("workbook_name", "")
        dashboard_names = row.get("dashboard_names", []) or []
        
        # Rule-based assessment
        complexity, reasoning = determine_visualization_complexity(mark_class, encoding, rules)
        
        # LLM fallback for ambiguous cases
        if complexity == "medium" and not mark_class:
            try:
                prompt = build_visualization_prompt(mark_class, encoding, worksheet_name, rules)
                response = llm.invoke(prompt)
                # Try to parse JSON from response
                content = response.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                llm_result = json.loads(content)
                complexity = llm_result.get("complexity", complexity)
                reasoning = llm_result.get("reasoning", reasoning)
            except Exception as e:
                # Fallback to rule-based if LLM fails
                pass
        
        # Map mark_class to feature name
        feature_map = {
            "bar": "Bar Chart",
            "line": "Line Chart",
            "pie": "Pie Chart",
            "text": "Text Table",
            "square": "Square Chart",
            "circle": "Circle Chart",
            "shape": "Shape Chart",
            "map": "Map",
            "gantt": "Gantt Chart"
        }
        feature = feature_map.get(mark_class.lower(), mark_class.title())
        
        results.append({
            "feature_area": "Charts",
            "feature": feature,
            "complexity": complexity.capitalize(),
            "worksheet_name": worksheet_name,
            "workbook_name": workbook_name,
            "dashboard_names": dashboard_names
        })
    
    return json.dumps({"visualization_complexity": results}, indent=2)


@tool
def analyze_calculated_field_complexity() -> str:
    """
    Analyze calculated field complexity from fields table.
    Uses SQL agent to execute query dynamically with natural language.
    Returns JSON string with per-instance complexity analysis.
    """
    rules = load_complexity_rules("tableau").get("calculated_fields", {})
    results = []
    
    # Natural language query for SQL agent
    natural_language_query = """Get all calculated fields with their field name, formula, workbook name, and worksheet name. Only include fields where is_calculated is true and formula is not empty."""
    
    # Use SQL agent to execute query and get structured results
    rows = query_with_sql_agent(natural_language_query)
    
    # Fallback to direct query if SQL agent fails
    if not rows:
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT
                      f.caption as field_name,
                      f.formula,
                      wb.name as workbook_name,
                      wks.name as worksheet_name
                    FROM fields f
                    JOIN datasources ds ON f.datasource_id = ds.id
                    JOIN workbooks wb ON ds.workbook_id = wb.id
                    LEFT JOIN worksheets wks ON wks.datasource_id = ds.id
                    WHERE f.is_calculated = TRUE AND f.formula IS NOT NULL AND f.formula != ''
                """)
                rows = cur.fetchall()
        finally:
            conn.close()
    
    # Process results
    for row in rows:
        field_name = row.get("field_name", "")
        formula = row.get("formula", "")
        workbook_name = row.get("workbook_name", "")
        worksheet_name = row.get("worksheet_name", "")
        
        # Rule-based assessment
        complexity, matched_patterns = determine_calculated_field_complexity(formula, rules)
        
        # LLM fallback for ambiguous cases
        if complexity == "medium" and len(matched_patterns) == 0:
            try:
                prompt = build_calculated_field_prompt(field_name, formula, rules)
                response = llm.invoke(prompt)
                content = response.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                llm_result = json.loads(content)
                complexity = llm_result.get("complexity", complexity)
            except Exception as e:
                # Fallback to rule-based if LLM fails
                pass
        
        # Determine feature type
        if "LOD" in formula.upper() or "{" in formula:
            feature = "Level Of Detail"
        elif any(func in formula.upper() for func in ["WINDOW_", "RUNNING_", "RANK_"]):
            feature = "Table Calculation"
        else:
            feature = "Basic Calculated field"
        
        results.append({
            "feature_area": "Calculated Fields",
            "feature": feature,
            "complexity": complexity.capitalize(),
            "field_name": field_name,
            "formula": formula,
            "worksheet_name": worksheet_name or "",
            "workbook_name": workbook_name
        })
    
    return json.dumps({"calculated_field_complexity": results}, indent=2)


@tool
def analyze_dashboard_complexity() -> str:
    """
    Analyze dashboard complexity from dashboards, dashboard_components, and actions.
    Uses SQL agent to generate queries dynamically with natural language.
    Returns JSON string with per-instance complexity analysis.
    """
    rules = load_complexity_rules("tableau").get("dashboards", {})
    action_rules = load_complexity_rules("tableau").get("actions", {})
    results = []
    
    # Natural language queries for SQL agent
    dashboard_query = """Get all dashboards with their name, workbook name, number of components, and action types used in the workbook."""
    
    action_query = """Get all actions with their name, action type, source worksheet, target object, dashboard name, and workbook name. Only include actions where action_type is not null."""
    
    # Use SQL agent to execute queries and get structured results
    rows = query_with_sql_agent(dashboard_query)
    action_rows = query_with_sql_agent(action_query)
    
    # Fallback to direct queries if SQL agent fails
    if not rows or not action_rows:
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get dashboard complexity
                if not rows:
                    cur.execute("""
                        SELECT 
                          d.name as dashboard_name,
                          wb.name as workbook_name,
                          COUNT(DISTINCT dc.id) as component_count,
                          ARRAY_AGG(DISTINCT a.action_type) FILTER (WHERE a.action_type IS NOT NULL) as action_types
                        FROM dashboards d
                        JOIN workbooks wb ON d.workbook_id = wb.id
                        LEFT JOIN dashboard_components dc ON dc.dashboard_id = d.id
                        LEFT JOIN actions a ON a.workbook_id = wb.id
                        GROUP BY d.name, wb.name
                    """)
                    rows = cur.fetchall()
                
                # Get action complexity
                if not action_rows:
                    cur.execute("""
                        SELECT DISTINCT
                          a.name as action_name,
                          a.action_type,
                          a.source_object_name as source_worksheet,
                          a.target_object_name,
                          d.name as dashboard_name,
                          wb.name as workbook_name
                        FROM actions a
                        JOIN workbooks wb ON a.workbook_id = wb.id
                        LEFT JOIN dashboards d ON d.workbook_id = wb.id
                        WHERE a.action_type IS NOT NULL
                    """)
                    action_rows = cur.fetchall()
        finally:
            conn.close()
    
    # Process dashboard results
    for row in rows:
        dashboard_name = row.get("dashboard_name", "")
        workbook_name = row.get("workbook_name", "")
        component_count = row.get("component_count", 0) or 0
        action_types = row.get("action_types", []) or []
        
        # Rule-based assessment
        complexity, matched_indicators = determine_dashboard_complexity(
            component_count, action_types, {**rules, "actions": action_rules}
        )
        
        # LLM fallback for ambiguous cases
        if complexity == "medium" and component_count == 0:
            try:
                prompt = build_dashboard_prompt(dashboard_name, component_count, action_types, rules)
                response = llm.invoke(prompt)
                content = response.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                llm_result = json.loads(content)
                complexity = llm_result.get("complexity", complexity)
            except Exception as e:
                # Fallback to rule-based if LLM fails
                pass
        
        # Determine feature
        if component_count > 5:
            feature = "Multi Tile dashboard"
        else:
            feature = "Single Tile dashboard"
        
        results.append({
            "feature_area": "Dashboards",
            "feature": feature,
            "complexity": complexity.capitalize(),
            "dashboard_name": dashboard_name,
            "workbook_name": workbook_name,
            "component_count": component_count
        })
    
    # Process action results
    for row in action_rows:
        action_name = row.get("action_name", "")
        action_type = row.get("action_type", "")
        source_worksheet = row.get("source_worksheet", "")
        target_object = row.get("target_object_name", "")
        dashboard_name = row.get("dashboard_name", "")
        workbook_name = row.get("workbook_name", "")
        
        # Determine complexity from action type
        complexity = "low"
        for level in ["high", "medium", "low"]:
            level_action_types = action_rules.get(level, {}).get("action_types", [])
            if action_type.lower() in [at.lower() for at in level_action_types]:
                complexity = level
                break
        
        # Map action type to feature
        feature_map = {
            "filter": "Filter Action",
            "highlight": "Highlight Action",
            "url": "URL Action",
            "cross_filter": "Cross-filtering",
            "set_action": "Set Action",
            "parameter_action": "Parameter Action"
        }
        feature = feature_map.get(action_type.lower(), action_type.title())
        
        results.append({
            "feature_area": "Actions",
            "feature": feature,
            "complexity": complexity.capitalize(),
            "action_name": action_name,
            "dashboard_name": dashboard_name or "",
            "workbook_name": workbook_name,
            "source_worksheet": source_worksheet or "",
            "target_worksheets": [target_object] if target_object else []
        })
    
    return json.dumps({"dashboard_complexity": results}, indent=2)


# ============================================================================
# AGENT STATE
# ============================================================================

class ComplexityState(TypedDict):
    """State for complexity analysis workflow."""
    analysis_results: Dict[str, Any]
    messages: Annotated[List, operator.add]


# ============================================================================
# WORKFLOW NODES
# ============================================================================

def analyze_visualizations_node(state: ComplexityState) -> ComplexityState:
    """Node to analyze visualization complexity."""
    result = analyze_visualization_complexity.invoke({})
    viz_results = json.loads(result)
    
    current_results = state.get("analysis_results", {})
    current_results.update(viz_results)
    
    return {
        "analysis_results": current_results,
        "messages": [HumanMessage(content=f"Visualization analysis complete: {len(viz_results.get('visualization_complexity', []))} visualizations analyzed")]
    }


def analyze_calculated_fields_node(state: ComplexityState) -> ComplexityState:
    """Node to analyze calculated field complexity."""
    result = analyze_calculated_field_complexity.invoke({})
    calc_results = json.loads(result)
    
    current_results = state.get("analysis_results", {})
    current_results.update(calc_results)
    
    return {
        "analysis_results": current_results,
        "messages": [HumanMessage(content=f"Calculated field analysis complete: {len(calc_results.get('calculated_field_complexity', []))} fields analyzed")]
    }


def analyze_dashboards_node(state: ComplexityState) -> ComplexityState:
    """Node to analyze dashboard complexity."""
    result = analyze_dashboard_complexity.invoke({})
    dash_results = json.loads(result)
    
    current_results = state.get("analysis_results", {})
    current_results.update(dash_results)
    
    return {
        "analysis_results": current_results,
        "messages": [HumanMessage(content=f"Dashboard analysis complete: {len(dash_results.get('dashboard_complexity', []))} dashboards/actions analyzed")]
    }


def generate_report_node(state: ComplexityState) -> ComplexityState:
    """Node to generate final report."""
    results = state.get("analysis_results", {})
    
    # Combine all results into final JSON structure
    final_report = {
        "visualization_complexity": results.get("visualization_complexity", []),
        "calculated_field_complexity": results.get("calculated_field_complexity", []),
        "dashboard_complexity": results.get("dashboard_complexity", [])
    }
    
    return {
        "analysis_results": final_report,
        "messages": [HumanMessage(content=f"Final report generated with {len(final_report['visualization_complexity'])} visualizations, {len(final_report['calculated_field_complexity'])} calculated fields, and {len(final_report['dashboard_complexity'])} dashboards/actions")]
    }


# ============================================================================
# WORKFLOW
# ============================================================================

def create_complexity_agent():
    """Create the complexity analysis agent workflow."""
    workflow = StateGraph(ComplexityState)
    
    workflow.add_node("analyze_visualizations", analyze_visualizations_node)
    workflow.add_node("analyze_calculated_fields", analyze_calculated_fields_node)
    workflow.add_node("analyze_dashboards", analyze_dashboards_node)
    workflow.add_node("generate_report", generate_report_node)
    
    workflow.set_entry_point("analyze_visualizations")
    workflow.add_edge("analyze_visualizations", "analyze_calculated_fields")
    workflow.add_edge("analyze_calculated_fields", "analyze_dashboards")
    workflow.add_edge("analyze_dashboards", "generate_report")
    workflow.add_edge("generate_report", END)
    
    return workflow.compile()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point for complexity analysis agent."""
    print("=" * 60)
    print("🔍 Complexity Analysis Agent")
    print("=" * 60)
    print("Analyzing Tableau features for migration complexity...\n")
    
    agent = create_complexity_agent()
    
    result = agent.invoke({
        "analysis_results": {},
        "messages": []
    })
    
    # Print results
    print("\n" + "=" * 60)
    print("📊 COMPLEXITY ANALYSIS RESULTS")
    print("=" * 60)
    
    results = result.get("analysis_results", {})
    print(json.dumps(results, indent=2))
    
    # Save to file
    output_file = "evaluations/complexity_analysis_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {output_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
