# Agent 2 and Agent 3 Instructions - Data Preparation for Tableau Complexity Analysis

## Project Context

We are building an agentic system to analyze Tableau workbooks and prepare structured data for complexity scoring (specifically for Looker migration assessment).

**Goal:** Extract clean, structured data from Tableau files that will later be used to calculate dashboard complexity.

---

## Current State

✅ **Agent 1 Complete:** 
- Explores Tableau XML files
- Converts to JSON
- Creates basic inventory
- Can answer queries using JsonToolkit
- Has both exploration mode and query mode

---

## What We Need to Build

### **Agent 2: Feature Schema Designer**
Defines WHAT data to extract from each component type.

### **Agent 3: Data Extractor**
Extracts the ACTUAL values based on Agent 2's schema.

---

## Critical Requirements

❌ **DO NOT calculate complexity scores** - Agent 2 and 3 only prepare data
❌ **DO NOT score or rate components** - Just extract facts
✅ **DO extract comprehensive structured data**
✅ **DO maintain relationships between components**
✅ **DO use Agent 1's query mode** when needed

---

## Data to Extract

Based on migration complexity analysis (Tableau → Looker), we need to extract these features:

### **1. DASHBOARD Component**

**Basic Features:**
- dashboard_name (string)
- dashboard_id (string)

**Layout Complexity:**
- container_count (number) - total containers
- custom_container_count (number) - custom/image containers
- layout_complexity_score (simple calculation: containers + custom_containers)

**Filters:**
- simple_filter_count (number) - basic dimension/measure filters
- complex_filter_count (number) - dynamic, cascading, conditional filters
- total_filter_count (number)

**Interactivity/Actions:**
- filter_action_count (number)
- highlight_action_count (number)
- url_action_count (number)
- parameter_action_count (number)
- set_action_count (number)
- total_action_count (number)

**Parameters:**
- parameter_count (number)
- parameter_names (list of strings)

**Relationships:**
- worksheets_used (list of worksheet names)
- worksheet_count (number)

---

### **2. WORKSHEET Component**

**Basic Features:**
- worksheet_name (string)
- worksheet_id (string)
- datasource_name (string) - which datasource it uses

**Chart Type Detection:**
- explicit_chart_type (string) - what TWB XML says
- mark_type (string) - automatic/bar/line/pie/text/square/circle/shape/gantt_bar
- has_dual_axis (boolean)
- axis_count (number) - 1, 2, or more
- inferred_chart_type (string) - smart detection (e.g., "donut", "bullet", "gantt")

**Crosstab/Table Specifics (if applicable):**
- is_crosstab (boolean)
- row_dimension_levels (number) - levels of row nesting
- column_dimension_levels (number) - levels of column nesting
- has_subtotals (boolean)
- has_grand_totals (boolean)
- conditional_formatting_rule_count (number)

**Hierarchy/Drill-down (if applicable):**
- has_drill_down (boolean)
- drill_levels (number) - how many levels deep
- hierarchy_type (string) - "standard" or "custom"

**Multi-dimensional Grouping:**
- row_dimension_count (number) - dimensions on rows
- column_dimension_count (number) - dimensions on columns
- grouping_depth (number) - deepest nesting level

**Fields and Filters:**
- field_count (number)
- field_names (list of strings)
- filter_count (number)
- filter_names (list of strings)

**Visual Complexity:**
- has_color_encoding (boolean)
- color_field_count (number)
- has_size_encoding (boolean)
- has_reference_lines (boolean)
- reference_line_count (number)
- has_reference_bands (boolean)
- has_custom_formatting (boolean)

**Relationships:**
- calculations_used (list of calculation names)
- calculation_count (number)
- datasources_used (list of datasource names) - can be multiple if blended

---

### **3. DATASOURCE Component**

**Basic Features:**
- datasource_name (string)
- datasource_id (string)

**Connection:**
- connection_type (string) - "extract", "live", "blended"
- database_type (string) - "SQL Server", "PostgreSQL", "Excel", etc.

**Structure:**
- table_count (number)
- table_names (list of strings)
- dimension_count (number)
- measure_count (number)

**Complexity Indicators:**
- has_custom_sql (boolean)
- has_data_blending (boolean)
- join_count (number)
- join_types (list of strings) - "inner", "left", "right", "full", "cross"
- has_relationships (boolean) - new Tableau relationships vs joins

---

### **4. CALCULATION Component**

**Basic Features:**
- calculation_name (string)
- calculation_id (string)
- datasource_name (string) - which datasource it belongs to

**Formula:**
- formula (string) - the actual calculation formula
- formula_length (number) - character count

**Complexity Classification:**
- complexity_level (string) - "simple", "medium", "complex", "very_complex"
  - Simple: Basic math, simple aggregations
  - Medium: IF statements, string/date functions
  - Complex: LOD expressions, table calculations
  - Very Complex: Nested LOD, SCRIPT functions

**Specific Features:**
- has_lod (boolean) - Level of Detail expression
- lod_type (string) - "FIXED", "INCLUDE", "EXCLUDE", null if no LOD
- has_table_calculation (boolean) - RUNNING_SUM, RANK, etc.
- table_calc_type (string) - type of table calculation if applicable
- has_nested_calculations (boolean) - uses other calculations
- nesting_level (number) - how many levels deep
- has_script (boolean) - Python/R scripts

**Relationships:**
- used_in_worksheets (list of worksheet names)

---

### **5. RELATIONSHIPS Component**

This is a separate structure capturing component dependencies:

```json
{
  "relationships": {
    "dashboard_to_worksheets": {
      "Dashboard_Name": ["Worksheet1", "Worksheet2", ...]
    },
    "worksheet_to_datasources": {
      "Worksheet_Name": ["Datasource1", "Datasource2", ...]
    },
    "worksheet_to_calculations": {
      "Worksheet_Name": ["Calc1", "Calc2", ...]
    },
    "calculation_to_datasource": {
      "Calc_Name": "Datasource_Name"
    },
    "dashboard_actions": {
      "Dashboard_Name": [
        {
          "action_type": "filter",
          "source": "Worksheet1",
          "target": "Worksheet2"
        }
      ]
    }
  }
}
```

---

## Agent 2: Feature Schema Designer

### **Purpose**
Agent 2 has TWO jobs:
1. **Load template** - WHAT features to extract (controlled by us)
2. **Determine HOW** - Generate extraction methods for each feature

### **Key Principle**
```
Template = WHAT to extract (static, version controlled)
Agent 2 = HOW to extract (dynamic, intelligent)
```

### **Input**
- `state["inventory"]` - basic inventory from Agent 1
- Feature template (from config/template.py)

### **Process**

1. **Load Feature Template**
   - Read predefined list of features from template
   - These are the features WE control and define
   
2. **Analyze Inventory**
   - Check which features are already available in inventory
   - Identify which features need querying from Agent 1

3. **Generate Extraction Schema**
   - For each feature, determine extraction method:
     - **Direct**: Feature exists in inventory, read directly
     - **Query**: Need to ask Agent 1, generate appropriate query
   
4. **Output Complete Schema**
   ```json
   {
     "dashboard": {
       "dashboard_name": {
         "type": "string",
         "method": "direct",
         "source": "inventory"
       },
       "filter_count": {
         "type": "number",
         "method": "query",
         "source": "agent_1",
         "query_template": "How many filters are on dashboard '{name}'?"
       },
       "action_count": {
         "type": "number", 
         "method": "query",
         "source": "agent_1",
         "query_template": "How many actions exist on dashboard '{name}'?"
       }
     },
     "worksheet": {
       "worksheet_name": {
         "type": "string",
         "method": "direct",
         "source": "inventory"
       },
       "chart_type": {
         "type": "string",
         "method": "query",
         "source": "agent_1",
         "query_template": "What is the chart type of worksheet '{name}'?"
       },
       "field_count": {
         "type": "number",
         "method": "query",
         "source": "agent_1",
         "query_template": "How many fields does worksheet '{name}' have?"
       }
     }
   }
   ```

### **Implementation**

**Step 1: Create Template File**

Create `config/template.py`:
```python
"""
Feature Template - Defines WHAT to extract
We control and version this file
"""

DASHBOARD_FEATURES = [
    "dashboard_name",
    "dashboard_id",
    "container_count",
    "custom_container_count",
    "simple_filter_count",
    "complex_filter_count",
    "total_filter_count",
    "filter_action_count",
    "highlight_action_count",
    "url_action_count",
    "parameter_action_count",
    "set_action_count",
    "total_action_count",
    "parameter_count",
    "parameter_names",
    "worksheets_used",
    "worksheet_count"
]

WORKSHEET_FEATURES = [
    "worksheet_name",
    "worksheet_id",
    "datasource_name",
    "explicit_chart_type",
    "mark_type",
    "has_dual_axis",
    "axis_count",
    "inferred_chart_type",
    "is_crosstab",
    "row_dimension_levels",
    "column_dimension_levels",
    "has_subtotals",
    "has_grand_totals",
    "conditional_formatting_rule_count",
    "has_drill_down",
    "drill_levels",
    "hierarchy_type",
    "row_dimension_count",
    "column_dimension_count",
    "grouping_depth",
    "field_count",
    "field_names",
    "filter_count",
    "filter_names",
    "has_color_encoding",
    "color_field_count",
    "has_size_encoding",
    "has_reference_lines",
    "reference_line_count",
    "has_reference_bands",
    "has_custom_formatting",
    "calculations_used",
    "calculation_count",
    "datasources_used"
]

DATASOURCE_FEATURES = [
    "datasource_name",
    "datasource_id",
    "connection_type",
    "database_type",
    "table_count",
    "table_names",
    "dimension_count",
    "measure_count",
    "has_custom_sql",
    "has_data_blending",
    "join_count",
    "join_types",
    "has_relationships"
]

CALCULATION_FEATURES = [
    "calculation_name",
    "calculation_id",
    "datasource_name",
    "formula",
    "formula_length",
    "complexity_level",
    "has_lod",
    "lod_type",
    "has_table_calculation",
    "table_calc_type",
    "has_nested_calculations",
    "nesting_level",
    "has_script",
    "used_in_worksheets"
]
```

**Step 2: Implement Agent 2**

In `agents/agent_2.py`:
```python
def agent_2_schema_designer(state: AnalysisState) -> AnalysisState:
    """
    Agent 2: Load template (WHAT), determine HOW for each feature
    """
    
    print("\n" + "="*70)
    print("🤖 AGENT 2: FEATURE SCHEMA DESIGNER")
    print("="*70)
    
    # Load feature template (WHAT to extract)
    from config.template import (
        DASHBOARD_FEATURES, 
        WORKSHEET_FEATURES,
        DATASOURCE_FEATURES,
        CALCULATION_FEATURES
    )
    
    inventory = state["inventory"]
    
    print("\n📋 Loaded feature templates:")
    print(f"   • Dashboard features: {len(DASHBOARD_FEATURES)}")
    print(f"   • Worksheet features: {len(WORKSHEET_FEATURES)}")
    print(f"   • Datasource features: {len(DATASOURCE_FEATURES)}")
    print(f"   • Calculation features: {len(CALCULATION_FEATURES)}")
    
    # Generate extraction schema (HOW to extract each feature)
    schema = {
        "dashboard": generate_component_schema("dashboard", DASHBOARD_FEATURES, inventory),
        "worksheet": generate_component_schema("worksheet", WORKSHEET_FEATURES, inventory),
        "datasource": generate_component_schema("datasource", DATASOURCE_FEATURES, inventory),
        "calculation": generate_component_schema("calculation", CALCULATION_FEATURES, inventory)
    }
    
    state["feature_schema"] = schema
    
    print("\n✅ Schema generated with extraction methods")
    print("="*70)
    
    return state


def generate_component_schema(component_type, features, inventory):
    """
    For each feature, determine HOW to extract it
    """
    schema = {}
    
    # Sample component to check what's available
    sample = get_sample_component(component_type, inventory)
    
    for feature in features:
        # Check if feature exists in inventory already
        if sample and feature in sample:
            schema[feature] = {
                "type": infer_type(sample[feature]),
                "method": "direct",
                "source": "inventory"
            }
        else:
            # Need to query Agent 1
            schema[feature] = {
                "type": infer_type_from_name(feature),
                "method": "query",
                "source": "agent_1",
                "query_template": generate_query_template(component_type, feature)
            }
    
    return schema


def generate_query_template(component_type, feature):
    """
    Generate appropriate query for Agent 1 based on feature
    """
    queries = {
        "filter_count": "How many filters are on {component_type} '{name}'?",
        "action_count": "How many actions exist on {component_type} '{name}'?",
        "field_count": "How many fields does {component_type} '{name}' have?",
        "chart_type": "What is the chart type of {component_type} '{name}'?",
        "has_dual_axis": "Does {component_type} '{name}' have dual axis?",
        # ... add more mappings
    }
    
    return queries.get(feature, f"What is the {feature} of {component_type} '{{name}}'?")
```

### **Output**
- Store in `state["feature_schema"]`
- Schema includes both WHAT and HOW for Agent 3

### **File Location**
- `config/template.py` - Feature template (WHAT to extract)
- `agents/agent_2.py` - Schema generator (HOW to extract)
- Function: `agent_2_schema_designer(state: AnalysisState) -> AnalysisState`

---

## Agent 3: Data Extractor

### **Purpose**
Extract actual values for all features using the schema from Agent 2.

**Key:** Agent 3 reads the schema and follows extraction methods!

### **Input**
- `state["inventory"]` - from Agent 1
- `state["feature_schema"]` - from Agent 2 (includes WHAT and HOW)
- Access to `query_tableau_expert()` - to ask Agent 1 questions

### **How Agent 3 Uses Agent 2's Output**

Agent 2 provides schema like:
```json
{
  "dashboard": {
    "dashboard_name": {
      "method": "direct",
      "source": "inventory"
    },
    "filter_count": {
      "method": "query",
      "source": "agent_1",
      "query_template": "How many filters on dashboard '{name}'?"
    }
  }
}
```

Agent 3 reads this and:
1. For "direct" method → Read from inventory
2. For "query" method → Query Agent 1 using template

### **Process**

**For each component type (dashboard, worksheet, datasource, calculation):**

1. **Get list of components** from inventory
   ```python
   dashboards = inventory["dashboards"]  # List of dashboard names/IDs
   ```

2. **Get extraction schema** for this component type
   ```python
   schema = feature_schema["dashboard"]
   ```

3. **For EACH component instance:**
   
   a. **Initialize empty feature dict**
   ```python
   extracted = {}
   ```
   
   b. **For EACH feature in schema:**
   ```python
   for feature_name, extraction_info in schema.items():
       if extraction_info["method"] == "direct":
           # Read from inventory
           extracted[feature_name] = read_from_inventory(component, feature_name)
       
       elif extraction_info["method"] == "query":
           # Query Agent 1
           query = extraction_info["query_template"].format(name=component_name)
           answer = query_tableau_expert(state, query, "agent_3")
           extracted[feature_name] = parse_answer(answer, extraction_info["type"])
   ```
   
   c. **Store extracted data**
   ```python
   all_extracted["dashboards"].append(extracted)
   ```

4. **Build relationships** - map connections between components

5. **Validate data** - check for missing/invalid values

### **Implementation Example**

```python
def agent_3_data_extractor(state: AnalysisState) -> AnalysisState:
    """
    Agent 3: Extract data using schema from Agent 2
    """
    
    print("\n" + "="*70)
    print("🤖 AGENT 3: DATA EXTRACTOR")
    print("="*70)
    
    inventory = state["inventory"]
    schema = state["feature_schema"]
    
    extracted_data = {
        "dashboards": [],
        "worksheets": [],
        "datasources": [],
        "calculations": [],
        "relationships": {}
    }
    
    # Extract Dashboards
    print("\n📊 Extracting dashboard data...")
    for dashboard in inventory.get("dashboards", []):
        dashboard_data = extract_component_features(
            component_type="dashboard",
            component=dashboard,
            schema=schema["dashboard"],
            state=state
        )
        extracted_data["dashboards"].append(dashboard_data)
        print(f"   ✓ {dashboard_data.get('dashboard_name', 'Unknown')}")
    
    # Extract Worksheets
    print("\n📈 Extracting worksheet data...")
    for worksheet in inventory.get("worksheets", []):
        worksheet_data = extract_component_features(
            component_type="worksheet",
            component=worksheet,
            schema=schema["worksheet"],
            state=state
        )
        extracted_data["worksheets"].append(worksheet_data)
        print(f"   ✓ {worksheet_data.get('worksheet_name', 'Unknown')}")
    
    # Extract Datasources
    print("\n🗄️  Extracting datasource data...")
    for datasource in inventory.get("datasources", []):
        datasource_data = extract_component_features(
            component_type="datasource",
            component=datasource,
            schema=schema["datasource"],
            state=state
        )
        extracted_data["datasources"].append(datasource_data)
        print(f"   ✓ {datasource_data.get('datasource_name', 'Unknown')}")
    
    # Extract Calculations
    print("\n🔢 Extracting calculation data...")
    for calculation in inventory.get("calculations", []):
        calculation_data = extract_component_features(
            component_type="calculation",
            component=calculation,
            schema=schema["calculation"],
            state=state
        )
        extracted_data["calculations"].append(calculation_data)
        print(f"   ✓ {calculation_data.get('calculation_name', 'Unknown')}")
    
    # Build Relationships
    print("\n🔗 Building relationships...")
    extracted_data["relationships"] = build_relationships(extracted_data)
    
    state["extracted_features"] = extracted_data
    
    print("\n✅ Data extraction complete!")
    print(f"   • Dashboards: {len(extracted_data['dashboards'])}")
    print(f"   • Worksheets: {len(extracted_data['worksheets'])}")
    print(f"   • Datasources: {len(extracted_data['datasources'])}")
    print(f"   • Calculations: {len(extracted_data['calculations'])}")
    print("="*70)
    
    return state


def extract_component_features(component_type, component, schema, state):
    """
    Extract features for a single component following the schema
    
    Args:
        component_type: "dashboard", "worksheet", etc.
        component: The component dict from inventory
        schema: Extraction schema for this component type
        state: Current workflow state
    
    Returns:
        Dict with all extracted features
    """
    extracted = {}
    component_name = component.get("name") or component.get("@name", "Unknown")
    
    for feature_name, extraction_info in schema.items():
        try:
            if extraction_info["method"] == "direct":
                # Read directly from inventory/component
                value = component.get(feature_name)
                if value is None:
                    value = get_default_value(extraction_info["type"])
                extracted[feature_name] = value
            
            elif extraction_info["method"] == "query":
                # Query Agent 1
                query = extraction_info["query_template"].format(
                    name=component_name,
                    component_type=component_type
                )
                
                answer = query_tableau_expert(state, query, "agent_3")
                
                # Parse answer based on expected type
                value = parse_agent_answer(
                    answer, 
                    extraction_info["type"],
                    feature_name
                )
                
                extracted[feature_name] = value
        
        except Exception as e:
            print(f"   ⚠️  Error extracting {feature_name}: {e}")
            extracted[feature_name] = get_default_value(extraction_info["type"])
    
    return extracted


def parse_agent_answer(answer, expected_type, feature_name):
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
            import re
            numbers = re.findall(r'\d+', answer)
            return int(numbers[0]) if numbers else 0
        
        elif expected_type == "boolean":
            # Check for yes/no, true/false
            answer_lower = answer.lower()
            if "yes" in answer_lower or "true" in answer_lower:
                return True
            elif "no" in answer_lower or "false" in answer_lower:
                return False
            return False
        
        elif expected_type == "list":
            # Try to extract list items
            # Look for comma-separated values or JSON array
            if "[" in answer and "]" in answer:
                import json
                return json.loads(answer[answer.find("["):answer.rfind("]")+1])
            elif "," in answer:
                return [item.strip() for item in answer.split(",")]
            return []
        
        else:  # string
            return answer.strip()
    
    except Exception as e:
        print(f"   ⚠️  Failed to parse {feature_name}: {e}")
        return get_default_value(expected_type)


def get_default_value(data_type):
    """Return default value for a data type"""
    defaults = {
        "string": "",
        "number": 0,
        "boolean": False,
        "list": []
    }
    return defaults.get(data_type, None)


def build_relationships(extracted_data):
    """
    Build relationship mappings between components
    
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
    for dashboard in extracted_data["dashboards"]:
        name = dashboard.get("dashboard_name")
        worksheets = dashboard.get("worksheets_used", [])
        if name and worksheets:
            relationships["dashboard_to_worksheets"][name] = worksheets
    
    # Worksheet → Datasources
    for worksheet in extracted_data["worksheets"]:
        name = worksheet.get("worksheet_name")
        datasources = worksheet.get("datasources_used", [])
        if name and datasources:
            relationships["worksheet_to_datasources"][name] = datasources
    
    # Worksheet → Calculations
    for worksheet in extracted_data["worksheets"]:
        name = worksheet.get("worksheet_name")
        calcs = worksheet.get("calculations_used", [])
        if name and calcs:
            relationships["worksheet_to_calculations"][name] = calcs
    
    # Calculation → Datasource
    for calc in extracted_data["calculations"]:
        name = calc.get("calculation_name")
        datasource = calc.get("datasource_name")
        if name and datasource:
            relationships["calculation_to_datasource"][name] = datasource
    
    return relationships
```

### **Key Points for Agent 3**

1. **Follow the Schema** - Don't hardcode what to extract, read from schema

2. **Handle Two Methods:**
   - `method: "direct"` → Read from inventory
   - `method: "query"` → Query Agent 1

3. **Parse Responses** - Agent 1 returns text, convert to correct data type

4. **Error Handling** - If extraction fails, use default values, don't crash

5. **Build Relationships** - Map connections between components

6. **Logging** - Show progress as extraction happens

### **Query Examples**

Based on schema, Agent 3 will ask Agent 1:

```python
# For dashboards
"How many filters are on dashboard 'Sales Overview'?"
"How many actions exist on dashboard 'Sales Overview'?"
"Which worksheets are used in dashboard 'Sales Overview'?"

# For worksheets
"What is the chart type of worksheet 'Sales Chart'?"
"How many fields does worksheet 'Sales Chart' have?"
"Does worksheet 'Sales Chart' have dual axis?"
"What datasource does worksheet 'Sales Chart' use?"
"What calculations are used in worksheet 'Sales Chart'?"

# For datasources
"What tables are in datasource 'Orders'?"
"What is the connection type of datasource 'Orders'?"
"Does datasource 'Orders' have custom SQL?"

# For calculations
"What is the formula for calculation 'Total Revenue'?"
"Does calculation 'Total Revenue' use LOD expressions?"
"What type of LOD is used in calculation 'Total Revenue'?"
```

### **Output Structure**

```json
{
  "extracted_features": {
    "dashboards": [
      {
        "dashboard_name": "Sales Overview",
        "container_count": 8,
        "simple_filter_count": 3,
        "complex_filter_count": 2,
        "total_action_count": 5,
        "worksheets_used": ["Sales Chart", "Revenue Trend"],
        ...
      }
    ],
    "worksheets": [
      {
        "worksheet_name": "Sales Chart",
        "explicit_chart_type": "bar",
        "mark_type": "automatic",
        "has_dual_axis": false,
        "field_count": 18,
        "datasource_name": "Orders",
        "calculations_used": ["Total Revenue", "Profit Margin"],
        ...
      }
    ],
    "datasources": [...],
    "calculations": [...],
    "relationships": {...}
  }
}
```

### **Output**
- Store in `state["extracted_features"]`
- This is the final prepared data ready for complexity analysis

### **File Location**
- `agents/agent_3.py`
- Function: `agent_3_data_extractor(state: AnalysisState) -> AnalysisState`

---

## State Updates

### **Update `models/state.py`**

Add new fields:

```python
class AnalysisState(TypedDict):
    # Existing fields
    bi_tool_type: str
    file_path: str
    file_json: Dict[str, Any]
    inventory: Dict[str, Any]
    agent_1_ready: bool
    agent_conversations: List[Dict]
    errors: List[str]
    
    # NEW: Agent 2 output
    feature_schema: Dict[str, Any]
    
    # NEW: Agent 3 output  
    extracted_features: Dict[str, Any]
    
    # Future: Agent 4-8
    complexity_scores: Dict[str, Any]
```

---

## Testing Strategy

### **Test Agent 2:**
```python
# After Agent 1 completes
state = agent_2_schema_designer(state)

# Verify
assert "feature_schema" in state
assert "dashboard_schema" in state["feature_schema"]
assert "worksheet_schema" in state["feature_schema"]
print("Schema generated:", state["feature_schema"])
```

### **Test Agent 3:**
```python
# After Agent 2 completes
state = agent_3_data_extractor(state)

# Verify
assert "extracted_features" in state
assert len(state["extracted_features"]["dashboards"]) > 0
assert len(state["extracted_features"]["worksheets"]) > 0
print("Extracted data:", state["extracted_features"])
```

### **End-to-End Test:**
```python
# Run all three agents
state = agent_1_explore(initial_state)      # Explore file
state = agent_2_schema_designer(state)       # Define schema
state = agent_3_data_extractor(state)        # Extract data

# Verify complete pipeline
print("Dashboard features:", state["extracted_features"]["dashboards"][0])
```

---

## Implementation Guidance

### **For Agent 2:**

**Recommended Approach:** Template-based with predefined schema

1. Create a schema configuration (could be JSON or Python dict)
2. Load and return the schema
3. Optionally: Use LLM to validate schema against actual inventory

**Keep it simple for POC!**

### **For Agent 3:**

**Recommended Approach:** Query-based extraction

1. Loop through each component in inventory
2. For each component, ask Agent 1 multiple questions
3. Parse Agent 1's responses
4. Build structured output
5. Handle errors gracefully (if Agent 1 can't answer, store null/default)

**Use Agent 1's query mode heavily!**

---

## Success Criteria

✅ Agent 2 produces complete feature schema
✅ Agent 3 extracts all features for all components
✅ Output is clean JSON structure
✅ Relationships are captured
✅ Data is ready for complexity analysis (future agents)
✅ No complexity scoring happens yet (that's Agent 4-8)

---

## What Cursor Should Do

1. **Create `agents/agent_2.py`**
   - Implement `agent_2_schema_designer` function
   - Use template-based approach
   - Return comprehensive schema

2. **Create `agents/agent_3.py`**
   - Implement `agent_3_data_extractor` function
   - Use `query_tableau_expert` to ask Agent 1 questions
   - Extract all features per schema
   - Build relationship mapping

3. **Update `models/state.py`**
   - Add `feature_schema` field
   - Add `extracted_features` field

4. **Create `tests/test_agent_2.py`**
   - Test schema generation

5. **Create `tests/test_agent_3.py`**
   - Test data extraction

6. **Update `main.py`**
   - Add Agent 2 and 3 to workflow

---

## Architecture Reminder

```
Agent 1: Domain Expert (DONE ✅)
    ↓ Creates inventory
Agent 2: Schema Designer (TO BUILD)
    ↓ Defines what to extract
Agent 3: Data Extractor (TO BUILD)
    ↓ Extracts actual values
[Prepared Data - Ready for Analysis]

Future:
Agent 4-8: Complexity Calculators
    ↓ Calculate scores
[Complexity Results]
```

---

## Notes

- **DO NOT overcomplicate** - Start simple, iterate
- **USE Agent 1's query mode** - It's already built and working
- **YAML rules** - We have them for later, don't worry about now
- **Focus on data preparation** - Complexity scoring comes later
- **Chart type inference** - Extract both explicit and try to infer, but don't overthink it for POC

---

## Questions to Resolve During Implementation

1. Should Agent 3 batch queries to Agent 1 or ask one at a time?
2. How to handle missing data (component exists but can't extract feature)?
3. Should we validate extracted data types match schema?
4. How verbose should logging be?

Use best judgment for POC, prioritize working code over perfection!