# Complexity Analysis Agents Design

## Problem

After Parsing Agent extracts features and structure, we need to:
1. Analyze complexity for each component type (calculations, visualizations, datasources, filters, parameters)
2. Use LLM for nuanced analysis while preventing hallucination
3. Store complexity results in BigQuery for aggregation
4. Calculate aggregated complexity for containers (dashboards/reports) from related components
5. Support multiple BI platforms (Tableau, Power BI, Cognos, MicroStrategy)

## Solution

**Complexity Analysis Agents = LLM + Knowledge Base + BigQuery Storage**

- 6 separate agents (one per component type)
- LLM analyzes complexity with knowledge base reference (prevents hallucination)
- Store individual component complexity in BigQuery
- Dashboard Agent aggregates complexity from BigQuery via JOINs
- Platform-agnostic design

## Design

### Agent Architecture

```
Parsing Agent → parsed_* data
    ↓
Complexity Analysis Agents (parallel execution):
  ├─ Calculation Agent → analyze calculations → BigQuery (calculations table)
  ├─ Visualization Agent → analyze visualizations → BigQuery (visualizations table)
  ├─ Datasource Agent → analyze datasources → BigQuery (datasources table)
  ├─ Filter Agent → analyze filters → BigQuery (filters table)
  └─ Parameter Agent → analyze parameters → BigQuery (parameters table)
    ↓
Dashboard Agent → JOIN BigQuery tables → aggregate complexity → BigQuery (containers table)
```

## Implementation

### 1. Knowledge Base for Complexity Rules

**File:** `config/complexity_rules.json`

```json
{
  "looker_migration_complexity": {
    "calculations": {
      "low": {
        "indicators": ["basic_arithmetic", "simple_aggregation"],
        "examples": ["SUM([Sales])", "[Profit] / [Sales]"],
        "migration_effort": "1-2 hours"
      },
      "medium": {
        "indicators": ["conditional_logic", "date_functions", "string_operations"],
        "examples": ["IF [Sales] > 1000 THEN 'High' ELSE 'Low' END", "DATETRUNC('month', [Date])"],
        "migration_effort": "2-4 hours"
      },
      "high": {
        "indicators": ["window_functions", "lod_expressions", "table_calculations", "nested_functions"],
        "examples": ["WINDOW_AVG([Sales], -6, 0)", "{FIXED [Region] : SUM([Sales])}"],
        "migration_effort": "4-8 hours"
      }
    },
    "visualizations": {
      "low": {
        "indicators": ["simple_charts", "basic_filters", "single_datasource"],
        "chart_types": ["bar_chart", "line_chart", "pie_chart"],
        "migration_effort": "2-4 hours"
      },
      "medium": {
        "indicators": ["dual_axis", "multiple_datasources", "calculated_fields"],
        "chart_types": ["scatter_plot", "area_chart", "heatmap"],
        "migration_effort": "4-8 hours"
      },
      "high": {
        "indicators": ["complex_interactivity", "custom_mark_types", "table_calculations"],
        "chart_types": ["gantt_chart", "treemap", "custom_shapes"],
        "migration_effort": "8-16 hours"
      }
    },
    "datasources": {
      "low": {
        "types": ["bigquery", "postgresql", "mysql", "snowflake"],
        "looker_support": "fully_supported",
        "migration_effort": "1-2 hours"
      },
      "medium": {
        "types": ["sql_server", "oracle"],
        "looker_support": "supported",
        "migration_effort": "2-4 hours"
      },
      "high": {
        "types": ["hyper", "excel"],
        "looker_support": "not_supported",
        "migration_effort": "4-8 hours (requires ETL)"
      }
    },
    "filters": {
      "low": {
        "indicators": ["simple_dimension_filter", "basic_quick_filter"],
        "migration_effort": "1 hour"
      },
      "medium": {
        "indicators": ["measure_filter", "relative_date_filter"],
        "migration_effort": "2-3 hours"
      },
      "high": {
        "indicators": ["complex_expression", "cross_filter", "context_filter"],
        "migration_effort": "3-5 hours"
      }
    },
    "parameters": {
      "low": {
        "indicators": ["single_value", "simple_list"],
        "migration_effort": "1-2 hours"
      },
      "medium": {
        "indicators": ["date_range", "multi_select"],
        "migration_effort": "2-4 hours"
      },
      "high": {
        "indicators": ["dynamic_parameter", "calculated_parameter", "top_n"],
        "migration_effort": "4-8 hours"
      }
    }
  }
}
```

### 2. LLM Service Method for Complexity Analysis

**File:** `services/llm_service.py`

```python
async def analyze_complexity(
    self,
    component_type: str,
    component_data: Dict[str, Any],
    platform: str,
    complexity_rules: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Analyze component complexity using LLM with knowledge base reference.
    
    Args:
        component_type: Type of component (calculation, visualization, datasource, filter, parameter)
        component_data: Parsed component data (features, structure, formula, etc.)
        platform: BI platform (tableau, power_bi, cognos, microstrategy)
        complexity_rules: Knowledge base complexity rules
    
    Returns:
        Dict with complexity analysis:
        {
            "complexity": "low|medium|high",
            "complexity_reasoning": "LLM explanation",
            "complexity_indicators": [...],
            "migration_effort": "..."
        }
    """
    # Build prompt with:
    # - Component data
    # - Complexity rules from knowledge base
    # - Platform context
    # - Instructions to prevent hallucination
    
    # Call LLM
    # Parse response
    # Return structured output
```

### 3. Complexity Analysis Agents

#### 3.1 Calculation Agent

**File:** `agents/calculation_agent.py`

**Process:**
1. Read `parsed_calculations` from state
2. For each calculation:
   - Load complexity rules from knowledge base
   - Call LLM to analyze complexity (formula, structure, dependencies)
   - Store result in BigQuery `calculations` table
3. Write analysis to JSON file
4. Update state

**Output:**
- BigQuery: `calculations` table
- JSON: `calculation_analysis.json`
- State: `calculation_analysis`

#### 3.2 Visualization Agent

**File:** `agents/visualization_agent.py`

**Process:**
1. Read `parsed_worksheets` from state
2. For each visualization:
   - Load complexity rules from knowledge base
   - Call LLM to analyze complexity (chart_type, features, structure)
   - Store result in BigQuery `visualizations` table
3. Write analysis to JSON file
4. Update state

**Output:**
- BigQuery: `visualizations` table
- JSON: `visualization_analysis.json`
- State: `visualization_analysis`

#### 3.3 Datasource Agent

**File:** `agents/datasource_agent.py`

**Process:**
1. Read `parsed_datasources` from state
2. For each datasource:
   - Load complexity rules from knowledge base
   - Call LLM to analyze complexity (connection_type, looker_support)
   - Store result in BigQuery `datasources` table
3. Write analysis to JSON file
4. Update state

**Output:**
- BigQuery: `datasources` table
- JSON: `datasource_analysis.json`
- State: `datasource_analysis`

#### 3.4 Filter Agent (NEW)

**File:** `agents/filter_agent.py`

**Process:**
1. Read `parsed_filters` from state
2. For each filter:
   - Load complexity rules from knowledge base
   - Call LLM to analyze complexity (filter_type, expression, scope)
   - Store result in BigQuery `filters` table
3. Write analysis to JSON file
4. Update state

**Output:**
- BigQuery: `filters` table
- JSON: `filter_analysis.json`
- State: `filter_analysis`

#### 3.5 Parameter Agent (NEW)

**File:** `agents/parameter_agent.py`

**Process:**
1. Read `parsed_parameters` from state
2. For each parameter:
   - Load complexity rules from knowledge base
   - Call LLM to analyze complexity (parameter_type, scope, usage)
   - Store result in BigQuery `parameters` table
3. Write analysis to JSON file
4. Update state

**Output:**
- BigQuery: `parameters` table
- JSON: `parameter_analysis.json`
- State: `parameter_analysis`

#### 3.6 Dashboard Agent (Aggregation)

**File:** `agents/dashboard_agent.py`

**Process:**
1. Read `parsed_dashboards` from state
2. For each dashboard:
   - Calculate own complexity from features (using LLM + knowledge base)
   - Read related components from BigQuery:
     - JOIN `visualizations` table (by dependencies.worksheets[])
     - JOIN `datasources` table (by dependencies.datasources[])
     - JOIN `calculations` table (by dependencies.calculations[])
     - JOIN `filters` table (by dependencies.filters[])
     - JOIN `parameters` table (by dependencies.parameters[])
   - Aggregate complexity: `MAX(own_complexity, max_visualization_complexity, ...)`
   - Store aggregated result in BigQuery `containers` table
3. Write analysis to JSON file
4. Update state

**Output:**
- BigQuery: `containers` table (with aggregated complexity)
- JSON: `dashboard_analysis.json`
- State: `dashboard_analysis`

**Aggregation Logic:**
```python
# Dashboard complexity aggregation
dashboard_complexity = max(
    own_complexity,  # From dashboard features
    max_visualization_complexity,  # From JOINed visualizations
    max_datasource_complexity,  # From JOINed datasources
    max_calculation_complexity,  # From JOINed calculations
    max_filter_complexity,  # From JOINed filters
    max_parameter_complexity  # From JOINed parameters
)
```

## BigQuery Model

### Dataset: `bi_assessment`

### Table 1: `containers`

**Purpose:** Top-level containers (dashboards/reports) across all BI platforms

**Fields:**
- `platform` (STRING, REQUIRED) - tableau, power_bi, cognos, microstrategy
- `container_type` (STRING, REQUIRED) - dashboard, report
- `id` (STRING, REQUIRED) - unique container ID
- `name` (STRING, REQUIRED) - container name
- `workbook_name` (STRING, NULLABLE) - parent workbook/report name
- `features` (JSON, NULLABLE) - extracted features
  - `filters_count` (INTEGER)
  - `charts_count` (INTEGER)
  - `parameters_count` (INTEGER)
  - `interactivity` (ARRAY<STRING>)
- `structure` (JSON, NULLABLE) - structure information
  - `layout_type` (STRING)
  - `zones` (ARRAY<JSON>)
- `complexity` (STRING, REQUIRED) - low, medium, high (aggregated from related components)
- `dependencies` (JSON, NULLABLE) - related component IDs
  - `visualizations` (ARRAY<STRING>) - array of visualization IDs
  - `datasources` (ARRAY<STRING>) - array of datasource IDs
  - `calculations` (ARRAY<STRING>) - array of calculation field_names
  - `filters` (ARRAY<STRING>) - array of filter IDs
  - `parameters` (ARRAY<STRING>) - array of parameter IDs
- `job_id` (STRING, REQUIRED) - assessment job ID
- `created_at` (TIMESTAMP, REQUIRED) - record creation timestamp

**Primary Key:** `(platform, id, job_id)`

---

### Table 2: `visualizations`

**Purpose:** Visualizations/pages/worksheets across all BI platforms

**Fields:**
- `platform` (STRING, REQUIRED) - tableau, power_bi, cognos, microstrategy
- `visualization_type` (STRING, REQUIRED) - worksheet, page, visual, report
- `id` (STRING, REQUIRED) - unique visualization ID
- `name` (STRING, REQUIRED) - visualization name
- `features` (JSON, NULLABLE) - extracted features
  - `chart_type` (STRING)
  - `calculations_count` (INTEGER)
  - `filters_count` (INTEGER)
  - `interactivity` (ARRAY<STRING>)
- `structure` (JSON, NULLABLE) - structure information
  - `data_fields` (JSON)
  - `marks` (JSON)
- `complexity` (STRING, REQUIRED) - low, medium, high (own complexity from features)
- `complexity_reasoning` (STRING, NULLABLE) - LLM explanation
- `dependencies` (JSON, NULLABLE) - related component IDs
  - `datasources` (ARRAY<STRING>) - array of datasource IDs
  - `calculations` (ARRAY<STRING>) - array of calculation field_names
  - `filters` (ARRAY<STRING>) - array of filter IDs
- `job_id` (STRING, REQUIRED) - assessment job ID
- `created_at` (TIMESTAMP, REQUIRED) - record creation timestamp

**Primary Key:** `(platform, id, job_id)`

**Foreign Keys:**
- `dependencies.datasources[]` → `datasources.id`
- `dependencies.calculations[]` → `calculations.field_name`

---

### Table 3: `datasources`

**Purpose:** Data sources/connections across all BI platforms

**Fields:**
- `platform` (STRING, REQUIRED) - tableau, power_bi, cognos, microstrategy
- `datasource_type` (STRING, REQUIRED) - bigquery, sql, hyper, excel, etc.
- `id` (STRING, REQUIRED) - unique datasource ID
- `name` (STRING, REQUIRED) - datasource name
- `connection` (JSON, NULLABLE) - connection details
  - `type` (STRING)
  - `server` (STRING)
  - `database` (STRING)
  - `project` (STRING) - for BigQuery
  - `dataset` (STRING) - for BigQuery
- `complexity` (STRING, REQUIRED) - low, medium, high
- `complexity_reasoning` (STRING, NULLABLE) - LLM explanation
- `looker_support` (STRING, NULLABLE) - fully_supported, supported, not_supported
- `migration_complexity` (STRING, NULLABLE) - low, medium, high, critical
- `job_id` (STRING, REQUIRED) - assessment job ID
- `created_at` (TIMESTAMP, REQUIRED) - record creation timestamp

**Primary Key:** `(platform, id, job_id)`

---

### Table 4: `calculations`

**Purpose:** Calculations/measures/metrics across all BI platforms

**Fields:**
- `platform` (STRING, REQUIRED) - tableau, power_bi, cognos, microstrategy
- `calculation_type` (STRING, REQUIRED) - calculated_field, measure, metric
- `id` (STRING, NULLABLE) - calculation ID (if available)
- `field_name` (STRING, REQUIRED) - calculation name/field name (unique identifier)
- `datasource_id` (STRING, NULLABLE) - parent datasource ID (foreign key)
- `formula` (STRING, NULLABLE) - calculation formula/expression
- `formula_structure` (JSON, NULLABLE) - parsed formula structure
- `data_type` (STRING, NULLABLE) - string, number, date, boolean
- `aggregation` (STRING, NULLABLE) - sum, avg, count, none, etc.
- `complexity` (STRING, REQUIRED) - low, medium, high
- `complexity_reasoning` (STRING, NULLABLE) - LLM explanation
- `complexity_indicators` (JSON, NULLABLE) - complexity factors
  - `functions_used` (ARRAY<STRING>)
  - `nested_level` (INTEGER)
  - `dependencies_count` (INTEGER)
- `job_id` (STRING, REQUIRED) - assessment job ID
- `created_at` (TIMESTAMP, REQUIRED) - record creation timestamp

**Primary Key:** `(platform, field_name, job_id)`

**Foreign Keys:**
- `datasource_id` → `datasources.id`

---

### Table 5: `filters`

**Purpose:** Filters across all BI platforms

**Fields:**
- `platform` (STRING, REQUIRED) - tableau, power_bi, cognos, microstrategy
- `filter_type` (STRING, REQUIRED) - dimension, measure, quick_filter, etc.
- `id` (STRING, REQUIRED) - unique filter ID
- `name` (STRING, NULLABLE) - filter name
- `field` (STRING, NULLABLE) - field being filtered
- `expression` (STRING, NULLABLE) - filter expression/condition
- `scope` (STRING, NULLABLE) - worksheet, dashboard, global
- `complexity` (STRING, REQUIRED) - low, medium, high
- `complexity_reasoning` (STRING, NULLABLE) - LLM explanation
- `applied_to` (JSON, NULLABLE) - where filter is applied
  - `containers` (ARRAY<STRING>) - array of container IDs
  - `visualizations` (ARRAY<STRING>) - array of visualization IDs
- `dependencies` (JSON, NULLABLE) - related component IDs
  - `datasources` (ARRAY<STRING>) - array of datasource IDs
- `job_id` (STRING, REQUIRED) - assessment job ID
- `created_at` (TIMESTAMP, REQUIRED) - record creation timestamp

**Primary Key:** `(platform, id, job_id)`

**Foreign Keys:**
- `dependencies.datasources[]` → `datasources.id`
- `applied_to.containers[]` → `containers.id`
- `applied_to.visualizations[]` → `visualizations.id`

---

### Table 6: `parameters`

**Purpose:** Parameters across all BI platforms

**Fields:**
- `platform` (STRING, REQUIRED) - tableau, power_bi, cognos, microstrategy
- `parameter_type` (STRING, REQUIRED) - string, date, number, boolean
- `id` (STRING, REQUIRED) - unique parameter ID
- `name` (STRING, REQUIRED) - parameter name
- `data_type` (STRING, NULLABLE) - string, date, number, boolean
- `default_value` (STRING, NULLABLE) - default parameter value
- `allowed_values` (JSON, NULLABLE) - array of allowed values (if restricted)
- `scope` (STRING, NULLABLE) - workbook, dashboard, worksheet
- `complexity` (STRING, REQUIRED) - low, medium, high
- `complexity_reasoning` (STRING, NULLABLE) - LLM explanation
- `used_by` (JSON, NULLABLE) - where parameter is used
  - `containers` (ARRAY<STRING>) - array of container IDs
  - `visualizations` (ARRAY<STRING>) - array of visualization IDs
  - `calculations` (ARRAY<STRING>) - array of calculation field_names
- `job_id` (STRING, REQUIRED) - assessment job ID
- `created_at` (TIMESTAMP, REQUIRED) - record creation timestamp

**Primary Key:** `(platform, id, job_id)`

**Foreign Keys:**
- `used_by.containers[]` → `containers.id`
- `used_by.visualizations[]` → `visualizations.id`
- `used_by.calculations[]` → `calculations.field_name`

---

## Relationship Model

### Complexity Aggregation Flow

**Visualization Complexity (Aggregated via JOIN):**
```
visualization.complexity = MAX(
  own_complexity (from features),
  MAX(datasource_complexities),  -- from JOINed datasources
  MAX(calculation_complexities)   -- from JOINed calculations
)
```

**Container Complexity (Aggregated via JOIN):**
```
container.complexity = MAX(
  own_complexity (from features),
  MAX(visualization_complexities)  -- from JOINed visualizations
)
```

### JOIN Relationships

**Visualization → Datasources:**
```sql
SELECT 
  v.id,
  v.complexity as own_complexity,
  MAX(ds.complexity) as max_datasource_complexity
FROM visualizations v
LEFT JOIN UNNEST(v.dependencies.datasources) as ds_id
LEFT JOIN datasources ds 
  ON ds.platform = v.platform 
  AND ds.id = ds_id
  AND ds.job_id = v.job_id
GROUP BY v.id, v.complexity
```

**Visualization → Calculations:**
```sql
SELECT 
  v.id,
  v.complexity as own_complexity,
  MAX(calc.complexity) as max_calculation_complexity
FROM visualizations v
LEFT JOIN UNNEST(v.dependencies.calculations) as calc_name
LEFT JOIN calculations calc 
  ON calc.platform = v.platform 
  AND calc.field_name = calc_name
  AND calc.job_id = v.job_id
GROUP BY v.id, v.complexity
```

**Container → Visualizations:**
```sql
SELECT 
  c.id,
  c.complexity as own_complexity,
  MAX(v.complexity) as max_visualization_complexity,
  GREATEST(
    c.complexity,
    COALESCE(MAX(v.complexity), 'low')
  ) as aggregated_complexity
FROM containers c
LEFT JOIN UNNEST(c.dependencies.visualizations) as vis_id
LEFT JOIN visualizations v 
  ON v.platform = c.platform 
  AND v.id = vis_id
  AND v.job_id = c.job_id
GROUP BY c.id, c.complexity
```

## LLM Prompt Design

### Prompt Structure

```
You are analyzing a {component_type} from {platform} to assess migration complexity to Looker.

Component Data:
{component_data}

Complexity Rules (use these to prevent hallucination):
{complexity_rules}

Task:
1. Analyze the component's complexity for Looker migration
2. Reference the complexity rules provided (do not invent new rules)
3. Identify complexity level: low, medium, or high
4. Explain your reasoning
5. Identify specific complexity indicators

Return JSON:
{
  "complexity": "low|medium|high",
  "complexity_reasoning": "explanation",
  "complexity_indicators": [...],
  "migration_effort": "..."
}
```

## Benefits

- **Platform agnostic:** Works for all BI platforms
- **Prevents hallucination:** Uses knowledge base as reference
- **Flexible aggregation:** MAX, AVG, or other methods
- **Scalable:** BigQuery handles large datasets efficiently
- **Traceable:** Can trace complexity back to source components

## Edge Cases

1. **Missing dependencies:** Handle gracefully, use 'low' as default
2. **Circular dependencies:** Detect and log warning
3. **LLM timeout/error:** Retry with exponential backoff
4. **BigQuery write failure:** Log error, continue with other components
5. **Missing complexity rules:** Use default rules, log warning

## Testing Strategy

1. **Unit Test:** Test each agent with sample parsed data
2. **LLM Test:** Verify LLM calls with knowledge base
3. **BigQuery Test:** Verify table creation and data insertion
4. **Aggregation Test:** Verify JOIN queries for complexity aggregation
5. **Integration Test:** Full workflow from Parsing → Complexity Analysis → BigQuery
6. **Multi-platform Test:** Test with different BI platforms

