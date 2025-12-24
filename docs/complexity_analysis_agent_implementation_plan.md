# Complexity Analysis Agent Implementation Plan

## Overview
Create `evaluations/complexity_analysis_agent.py` - a unified agent that analyzes Tableau features from PostgreSQL and outputs per-instance complexity assessments. The agent uses a hybrid approach (rule-based + LLM) and follows the architectural pattern from `evaluations/xml_to_dict_agent.py`.

## Architecture

### Agent Structure
- **Single unified agent** with specialized tools (not separate agents as in UML)
- **PostgreSQL-based** (not BigQuery) - follows existing pattern
- **Hybrid complexity assessment**: Rule-based for standard cases, LLM for edge cases
- **Per-instance output**: Each record represents one feature instance with full context
- **JSON-based configuration**: Easy to maintain and update, supports future LLM auto-detection

### Database Schema (from `evaluations/xml_to_dict_agent.py`)
- `workbooks` (id, name)
- `worksheets` (id, workbook_id, name)
- `worksheet_elements` (id, worksheet_id, mark_class, encoding JSONB, style JSONB)
- `fields` (id, datasource_id, caption, formula, is_calculated)
- `dashboards` (id, workbook_id, name)
- `dashboard_components` (id, dashboard_id, worksheet_id, component_type)
- `actions` (id, workbook_id, name, action_type, source_object_name, target_object_name)

## Configuration Management

### File Structure
```
config/
├── feature_catalog.json          # Existing - feature definitions
├── complexity_rules.json         # New - complexity assessment rules
└── complexity_rules.py          # New - helper functions to load rules
```

### 1. `config/complexity_rules.json` (NEW)

```json
{
  "tableau": {
    "visualizations": {
      "low": {
        "mark_classes": ["bar", "line", "pie", "text"],
        "indicators": ["single_axis", "basic_encoding"]
      },
      "medium": {
        "mark_classes": ["square", "circle", "shape", "map"],
        "indicators": ["dual_axis", "multiple_datasources", "custom_formatting"]
      },
      "high": {
        "mark_classes": ["gantt"],
        "indicators": ["custom_marks", "complex_encoding", "table_calculations"]
      }
    },
    "calculated_fields": {
      "low": {
        "patterns": ["basic_arithmetic", "simple_aggregation"],
        "regex": ["^SUM\\(|^AVG\\(|^COUNT\\(|^MIN\\(|^MAX\\("]
      },
      "medium": {
        "patterns": ["date_functions", "string_operations", "simple_lod"],
        "regex": ["DATETRUNC|DATEDIFF|DATEADD|LEFT|RIGHT|CONTAINS|REPLACE|\\{FIXED [^:]+: [^}]+\\}"]
      },
      "high": {
        "patterns": ["complex_lod", "window_functions", "nested_calculations"],
        "regex": ["WINDOW_|\\{FIXED.*:.*\\{FIXED|\\{INCLUDE|\\{EXCLUDE|\\{FIXED.*,.*:"]
      }
    },
    "dashboards": {
      "low": {
        "component_count_max": 1,
        "indicators": ["basic_filters", "data_labels", "single_worksheet"]
      },
      "medium": {
        "component_count_min": 2,
        "component_count_max": 5,
        "indicators": ["tooltips", "group_features", "detail_views", "multiple_worksheets"]
      },
      "high": {
        "component_count_min": 6,
        "indicators": ["cross_filtering", "hierarchy", "top_n", "highlight_actions", "multi_tile"]
      }
    },
    "actions": {
      "low": {
        "action_types": ["url"]
      },
      "medium": {
        "action_types": ["filter", "highlight"]
      },
      "high": {
        "action_types": ["cross_filter", "set_action", "parameter_action"]
      }
    }
  }
}
```

### 2. `config/complexity_rules.py` (NEW)

```python
"""Load and validate complexity rules from JSON configuration."""
import json
from pathlib import Path
from typing import Dict, Any, Optional

def load_complexity_rules(platform: str = "tableau") -> Dict[str, Any]:
    """Load complexity rules for the given platform."""
    rules_path = Path(__file__).parent / "complexity_rules.json"
    if not rules_path.exists():
        return {}
    
    with open(rules_path, 'r', encoding='utf-8') as f:
        full_rules = json.load(f)
    
    return full_rules.get(platform, {})
```

## LLM Prompt Design

### File: `evaluations/complexity_prompts.py` (NEW)

Simple template functions for each tool's LLM prompts:

#### 1. Visualization Complexity Prompt

```python
import json
from typing import Dict, Any

def build_visualization_prompt(
    mark_class: str,
    encoding: Dict[str, Any],
    worksheet_name: str,
    rules: Dict[str, Any]
) -> str:
    """Build prompt for LLM to assess visualization complexity."""
    
    return f"""Analyze this Tableau visualization for Looker migration complexity.

Visualization Details:
- Mark Class: {mark_class}
- Worksheet: {worksheet_name}
- Encoding: {json.dumps(encoding, indent=2)}

Complexity Rules (use these only - do not invent new rules):
{json.dumps(rules, indent=2)}

Task:
1. Determine complexity level: "low", "medium", or "high"
2. Match mark_class against the rules provided above
3. If dual-axis detected (multiple axes in encoding), increase to "medium" or "high"
4. If custom/complex encoding patterns, consider "high"

Return ONLY valid JSON (no markdown, no explanations):
{{
  "complexity": "low|medium|high",
  "reasoning": "Brief explanation matching the rules",
  "matched_rule": "Which rule category matched"
}}
"""
```

#### 2. Calculated Field Complexity Prompt

```python
def build_calculated_field_prompt(
    field_name: str,
    formula: str,
    rules: Dict[str, Any]
) -> str:
    """Build prompt for LLM to assess calculated field complexity."""
    
    return f"""Analyze this Tableau calculated field for Looker migration complexity.

Calculated Field Details:
- Field Name: {field_name}
- Formula: {formula}

Complexity Rules (use these only - do not invent new rules):
{json.dumps(rules, indent=2)}

Task:
1. Check formula against regex patterns in rules
2. Look for patterns: basic_arithmetic, date_functions, string_operations, lod_expressions, window_functions
3. Determine complexity: "low", "medium", or "high"
4. Match against rule patterns provided above

Return ONLY valid JSON (no markdown, no explanations):
{{
  "complexity": "low|medium|high",
  "reasoning": "Which pattern matched (e.g., 'Contains LOD expression')",
  "matched_patterns": ["pattern1", "pattern2"]
}}
"""
```

#### 3. Dashboard Complexity Prompt

```python
def build_dashboard_prompt(
    dashboard_name: str,
    component_count: int,
    action_types: list,
    rules: Dict[str, Any]
) -> str:
    """Build prompt for LLM to assess dashboard complexity."""
    
    return f"""Analyze this Tableau dashboard for Looker migration complexity.

Dashboard Details:
- Dashboard Name: {dashboard_name}
- Component Count: {component_count}
- Action Types: {', '.join(action_types) if action_types else 'None'}

Complexity Rules (use these only - do not invent new rules):
{json.dumps(rules, indent=2)}

Task:
1. Check component_count against rules (low: ≤1, medium: 2-5, high: ≥6)
2. Check action_types against rules
3. Determine complexity: "low", "medium", or "high"
4. Match against rule thresholds provided above

Return ONLY valid JSON (no markdown, no explanations):
{{
  "complexity": "low|medium|high",
  "reasoning": "Which rule matched (e.g., '6 components = high complexity')",
  "matched_indicators": ["multi_tile", "cross_filtering"]
}}
"""
```

#### 4. Generic Complexity Assessment Prompt (Fallback)

```python
def build_generic_complexity_prompt(
    feature_type: str,
    feature_data: Dict[str, Any],
    rules: Dict[str, Any]
) -> str:
    """Build generic prompt for ambiguous cases."""
    
    return f"""Analyze this Tableau {feature_type} for Looker migration complexity.

Feature Data:
{json.dumps(feature_data, indent=2)}

Complexity Rules (use these only - do not invent new rules):
{json.dumps(rules, indent=2)}

Task:
1. Analyze the feature data against the rules
2. Determine complexity: "low", "medium", or "high"
3. Reference the rules provided - do not invent new complexity levels
4. If no clear match, choose the closest rule match

Return ONLY valid JSON (no markdown, no explanations):
{{
  "complexity": "low|medium|high",
  "reasoning": "Explanation based on rules",
  "confidence": "high|medium|low"
}}
"""
```

## Implementation Details

### File: `evaluations/complexity_analysis_agent.py`

#### Configuration Section
```python
from config.complexity_rules import load_complexity_rules
from evaluations.complexity_prompts import (
    build_visualization_prompt,
    build_calculated_field_prompt,
    build_dashboard_prompt,
    build_generic_complexity_prompt
)
from langchain_google_vertexai import ChatVertexAI

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "tableau_migration",
    "user": "postgres",
    "password": "postgres"
}

DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

llm = ChatVertexAI(model="gemini-2.0-flash-001", temperature=0)
```

#### Tools to Implement

**Tool 1: `analyze_visualization_complexity()`**
- **Load rules**: `rules = load_complexity_rules("tableau")["visualizations"]`
- **Query**: Join `worksheet_elements` → `worksheets` → `workbooks` → `dashboards`
- **Rule-based logic first**: Check `mark_class` against rules
- **LLM fallback**: If ambiguous, use `build_visualization_prompt()` and call LLM
- **Output per instance**: feature_area, feature, complexity, worksheet_name, workbook_name, dashboard_names

**Tool 2: `analyze_calculated_field_complexity()`**
- **Load rules**: `rules = load_complexity_rules("tableau")["calculated_fields"]`
- **Query**: Join `fields` → `datasources` → `workbooks` → `worksheets`
- **Rule-based logic first**: Match formula against regex patterns
- **LLM fallback**: If ambiguous, use `build_calculated_field_prompt()` and call LLM
- **Output per instance**: feature_area, feature, complexity, field_name, formula, worksheet_name, workbook_name

**Tool 3: `analyze_dashboard_complexity()`**
- **Load rules**: `rules = load_complexity_rules("tableau")["dashboards"]`
- **Query**: Join `dashboards` → `dashboard_components` → `actions` → `workbooks`
- **Rule-based logic first**: Check component_count and action_types against rules
- **LLM fallback**: If ambiguous, use `build_dashboard_prompt()` and call LLM
- **Output per instance**: feature_area, feature, complexity, dashboard_name, workbook_name, component_count

**Tool 4: `assess_complexity_with_llm()`** (Generic fallback)
- **Purpose**: Use LLM for edge cases when rule-based logic is ambiguous
- **Uses**: `build_generic_complexity_prompt()`
- **Returns**: Complexity level with reasoning

#### Agent Workflow (LangGraph)
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class ComplexityState(TypedDict):
    analysis_results: dict
    messages: Annotated[list, operator.add]

def create_complexity_agent():
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
```

#### Output JSON Structure (Per-Instance)

```json
{
  "visualization_complexity": [
    {
      "feature_area": "Charts",
      "feature": "Bar Chart",
      "complexity": "Low",
      "worksheet_name": "Sales Overview",
      "workbook_name": "Sales Dashboard",
      "dashboard_names": ["Executive Dashboard", "Sales Report"]
    }
  ],
  "calculated_field_complexity": [
    {
      "feature_area": "Calculated Fields",
      "feature": "Basic Calculated field",
      "complexity": "Low",
      "field_name": "Profit Margin",
      "formula": "SUM([Profit]) / SUM([Sales])",
      "worksheet_name": "Sales Overview",
      "workbook_name": "Sales Dashboard"
    }
  ],
  "dashboard_complexity": [
    {
      "feature_area": "Dashboards",
      "feature": "Multi Tile dashboard",
      "complexity": "High",
      "dashboard_name": "Executive Dashboard",
      "workbook_name": "Sales Dashboard",
      "component_count": 8
    },
    {
      "feature_area": "Actions",
      "feature": "Cross-filtering",
      "complexity": "High",
      "action_name": "Filter Sales",
      "dashboard_name": "Executive Dashboard",
      "workbook_name": "Sales Dashboard",
      "source_worksheet": "Sales Overview",
      "target_worksheets": ["Revenue Analysis", "Profit Report"]
    }
  ]
}
```

## SQL Query Patterns

### Visualization Complexity Query
```sql
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
GROUP BY we.mark_class, wks.name, wb.name, we.encoding
```

### Calculated Field Complexity Query
```sql
SELECT DISTINCT
  f.caption as field_name,
  f.formula,
  wb.name as workbook_name,
  wks.name as worksheet_name
FROM fields f
JOIN datasources ds ON f.datasource_id = ds.id
JOIN workbooks wb ON ds.workbook_id = wb.id
LEFT JOIN worksheets wks ON wks.datasource_id = ds.id
WHERE f.is_calculated = TRUE AND f.formula IS NOT NULL
```

### Dashboard Complexity Query
```sql
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
```

## Files to Create

1. **Create**: `evaluations/complexity_analysis_agent.py` (~400-500 lines)
2. **Create**: `config/complexity_rules.json` (~150-200 lines)
3. **Create**: `config/complexity_rules.py` (~50-100 lines)
4. **Create**: `evaluations/complexity_prompts.py` (~150-200 lines)

## Implementation Order

1. Create `config/complexity_rules.json` with initial rules
2. Create `config/complexity_rules.py` loader
3. Create `evaluations/complexity_prompts.py` with prompt templates
4. Create `evaluations/complexity_analysis_agent.py` with tools and workflow
5. Test with sample data from PostgreSQL

## Future LLM Auto-Detection Support

The JSON structure allows easy programmatic updates. Future implementation:
- Add `_metadata` section to track rule sources
- LLM agent can detect new patterns and suggest rule updates
- Human review process before committing auto-detected rules
