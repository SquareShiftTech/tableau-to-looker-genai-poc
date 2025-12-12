# Parsing Agent - Feature Extraction & Structure Capture Design

## Problem

After Exploration Agent creates component index, we need to:
1. Extract detailed features from XML files using parsing instructions
2. Capture structure of each component (layout, hierarchy, relationships)
3. Support all component types (dashboards, worksheets, datasources, calculations, filters, parameters)
4. Provide structured data for complexity analysis and HTML report generation

## Solution

**Parsing Agent = Lightweight XML Parsing + Structure Capture**

- Use XML parsing tools (no LLM - lightweight)
- Follow `parsing_instructions` from Exploration Agent index
- Extract features AND structure for each component
- Support all component types

## Design

### Flow

```
1. Get discovered_components index from Exploration Agent
2. Get parsed_elements_paths (file locations) from File Analysis Agent
3. Extract workbook_name from source_files
4. For each component type (dashboards, worksheets, datasources, calculations, filters, parameters):
   ├─ For each component in index:
   │   ├─ Read XML file (from component.file)
   │   ├─ Get parsing_instructions for that component
   │   ├─ Use lightweight XML parsing:
   │   │   ├─ Extract features (using instructions)
   │   │   └─ Capture structure (layout, hierarchy, relationships)
   │   └─ Build parsed component with features + structure
   └─ Store in parsed_{component_type} list
5. Write all parsed data to JSON files
6. Output: parsed_dashboards, parsed_worksheets, parsed_datasources, parsed_calculations, parsed_filters, parsed_parameters
```

## Implementation

### 1. Component Structure Definitions

**Dashboard Structure:**
```python
{
    "id": "dash-1",
    "name": "Sales Dashboard",
    "workbook_name": "sales_workbook",
    "features": {
        "filters_count": 3,
        "worksheets_count": 5,
        "parameters_count": 2,
        "interactivity": ["filters", "parameters", "actions"]
    },
    "structure": {
        "layout_type": "multi_zone",  # single_zone, multi_zone
        "zones": [
            {
                "id": "zone-1",
                "worksheets": ["sheet-1", "sheet-2"],
                "position": {"x": 0, "y": 0, "width": 800, "height": 400},
                "filters": ["filter-1"]
            }
        ],
        "filters": {
            "location": "top",
            "count": 3,
            "types": ["quick_filter", "parameter"]
        },
        "parameters": {
            "count": 2,
            "types": ["string", "date"]
        }
    },
    "dependencies": {
        "worksheets": ["sheet-1", "sheet-2"],
        "datasources": ["ds-1"],
        "filters": ["filter-1", "filter-2"],
        "parameters": ["param-1"]
    }
}
```

**Worksheet Structure:**
```python
{
    "id": "sheet-1",
    "name": "Sales by Region",
    "features": {
        "chart_type": "bar_chart",
        "calculations_count": 5,
        "filters_count": 2,
        "interactivity": ["filters", "tooltips", "actions"]
    },
    "structure": {
        "chart_type": "bar_chart",
        "data_fields": {
            "rows": [
                {"name": "Region", "type": "dimension"}
            ],
            "columns": [
                {"name": "Sales", "type": "measure", "aggregation": "sum"}
            ],
            "filters": [
                {"name": "Year", "type": "dimension"}
            ],
            "marks": {
                "type": "bar",
                "color": {"field": "Category"},
                "size": {"field": "Sales"}
            }
        },
        "calculations": [
            {"id": "calc-1", "name": "Profit Margin", "formula": "..."}
        ],
        "filters": [
            {"id": "filter-1", "type": "dimension", "field": "Year"}
        ]
    },
    "dependencies": {
        "datasources": ["ds-1"],
        "calculations": ["calc-1", "calc-2"],
        "filters": ["filter-1"]
    }
}
```

**Datasource Structure:**
```python
{
    "id": "ds-1",
    "name": "Sales Database",
    "features": {
        "connection_type": "bigquery",
        "tables_count": 3,
        "fields_count": 25,
        "calculations_count": 10
    },
    "structure": {
        "connection": {
            "type": "bigquery",
            "project": "my-project",
            "dataset": "sales_data",
            "tables": ["orders", "customers", "products"]
        },
        "tables": [
            {
                "name": "orders",
                "fields": [
                    {"name": "order_id", "type": "string"},
                    {"name": "sales", "type": "number"}
                ]
            }
        ],
        "calculations": [
            {"id": "calc-1", "name": "Profit Margin", "formula": "..."}
        ]
    },
    "complexity": "medium"
}
```

**Calculation Structure:**
```python
{
    "id": "calc-1",
    "name": "Profit Margin",
    "datasource_id": "ds-1",
    "features": {
        "formula": "[Profit] / [Sales]",
        "data_type": "float",
        "aggregation": "none"
    },
    "structure": {
        "formula": "[Profit] / [Sales]",
        "formula_structure": {
            "type": "division",
            "left": {"type": "field", "name": "Profit"},
            "right": {"type": "field", "name": "Sales"}
        },
        "dependencies": {
            "fields_used": ["Profit", "Sales"],
            "functions_used": [],
            "complexity_indicators": []
        },
        "data_type": "float",
        "aggregation": "none"
    },
    "complexity": "low"
}
```

**Filter Structure:**
```python
{
    "id": "filter-1",
    "name": "Year Filter",
    "features": {
        "type": "dimension",
        "field": "Year",
        "applied_to": ["sheet-1", "sheet-2"]
    },
    "structure": {
        "filter_type": "dimension",
        "field": "Year",
        "expression": "Year >= 2020",
        "applied_to": {
            "worksheets": ["sheet-1", "sheet-2"],
            "dashboards": ["dash-1"]
        },
        "scope": "worksheet"  # worksheet, dashboard, global
    },
    "dependencies": {
        "datasources": ["ds-1"],
        "worksheets": ["sheet-1", "sheet-2"]
    }
}
```

**Parameter Structure:**
```python
{
    "id": "param-1",
    "name": "Month Selector",
    "features": {
        "type": "date",
        "used_by": ["dash-1", "sheet-1"]
    },
    "structure": {
        "parameter_type": "date",
        "data_type": "date",
        "default_value": "2024-01-01",
        "allowed_values": null,  # or list of values
        "used_by": {
            "dashboards": ["dash-1"],
            "worksheets": ["sheet-1"],
            "calculations": []
        },
        "scope": "workbook"  # workbook, dashboard, worksheet
    },
    "dependencies": {
        "dashboards": ["dash-1"],
        "worksheets": ["sheet-1"]
    }
}
```

### 2. Parsing Agent Implementation

**File:** `agents/parsing_agent.py`

**Key Functions:**

```python
async def parsing_agent(state: AssessmentState) -> AssessmentState:
    """
    Parsing Agent - Extract features and structure from components.
    
    INPUT: discovered_components index from Exploration Agent
    OUTPUT: parsed_dashboards, parsed_worksheets, parsed_datasources, 
            parsed_calculations, parsed_filters, parsed_parameters
    """
    # 1. Get index and files
    discovered_components = state.get('discovered_components', {})
    parsed_elements_paths = state.get('parsed_elements_paths', [])
    workbook_name = _extract_workbook_name(state.get('source_files', []))
    
    # 2. Create file map for quick lookup
    file_map = create_file_map(parsed_elements_paths)
    
    # 3. Parse each component type
    parsed_dashboards = parse_dashboards(
        discovered_components.get('components', {}).get('dashboards', []),
        file_map,
        workbook_name
    )
    
    parsed_worksheets = parse_worksheets(
        discovered_components.get('components', {}).get('worksheets', []),
        file_map
    )
    
    parsed_datasources = parse_datasources(
        discovered_components.get('components', {}).get('datasources', []),
        file_map
    )
    
    parsed_calculations = parse_calculations(
        discovered_components.get('components', {}).get('calculations', []),
        file_map
    )
    
    parsed_filters = parse_filters(
        discovered_components.get('components', {}).get('filters', []),
        file_map
    )
    
    parsed_parameters = parse_parameters(
        discovered_components.get('components', {}).get('parameters', []),
        file_map
    )
    
    # 4. Write to JSON files
    write_parsed_data(output_dir, {
        'parsed_dashboards': parsed_dashboards,
        'parsed_worksheets': parsed_worksheets,
        'parsed_datasources': parsed_datasources,
        'parsed_calculations': parsed_calculations,
        'parsed_filters': parsed_filters,
        'parsed_parameters': parsed_parameters
    })
    
    # 5. Update state
    state['parsed_dashboards'] = parsed_dashboards
    state['parsed_worksheets'] = parsed_worksheets
    state['parsed_datasources'] = parsed_datasources
    state['parsed_calculations'] = parsed_calculations
    state['parsed_filters'] = parsed_filters
    state['parsed_parameters'] = parsed_parameters
    
    return state
```

### 3. XML Parsing Utilities

**File:** `utils/xml_utils.py` (extend existing)

```python
def extract_features_from_xml(
    file_path: str,
    component_id: str,
    parsing_instructions: Dict[str, str]
) -> Dict[str, Any]:
    """
    Extract features from XML file using parsing instructions.
    
    Args:
        file_path: Path to XML file
        component_id: Component ID to extract
        parsing_instructions: Instructions from Exploration Agent index
    
    Returns:
        Dict with extracted features
    """
    # Parse XML
    # Follow parsing_instructions to extract features
    # Return features dict
```

```python
def extract_structure_from_xml(
    file_path: str,
    component_id: str,
    component_type: str
) -> Dict[str, Any]:
    """
    Extract structure from XML file.
    
    Args:
        file_path: Path to XML file
        component_id: Component ID
        component_type: Type of component (dashboard, worksheet, etc.)
    
    Returns:
        Dict with structure information
    """
    # Parse XML
    # Extract structure based on component type
    # Return structure dict
```

### 4. Component-Specific Parsing Functions

```python
def parse_dashboards(
    dashboards_index: List[Dict],
    file_map: Dict[str, str],
    workbook_name: str
) -> List[Dict[str, Any]]:
    """
    Parse dashboard components with features and structure.
    """
    parsed = []
    for dashboard in dashboards_index:
        file_path = dashboard.get('file')
        parsing_instructions = dashboard.get('parsing_instructions', {})
        
        # Read XML
        xml_content = read_xml_file(file_path)
        
        # Extract features using instructions
        features = extract_features_from_xml(file_path, dashboard['id'], parsing_instructions)
        
        # Extract structure
        structure = extract_dashboard_structure(xml_content, dashboard['id'])
        
        # Build parsed dashboard
        parsed.append({
            'workbook_name': workbook_name,
            'id': dashboard['id'],
            'name': dashboard['name'],
            'features': features,
            'structure': structure,
            'dependencies': extract_dependencies(dashboard, dashboards_index)
        })
    
    return parsed
```

Similar functions for:
- `parse_worksheets()`
- `parse_datasources()`
- `parse_calculations()`
- `parse_filters()`
- `parse_parameters()`

## Output Structure

**Files Written:**
- `output/{job_id}/parsed_dashboards.json`
- `output/{job_id}/parsed_worksheets.json`
- `output/{job_id}/parsed_datasources.json`
- `output/{job_id}/parsed_calculations.json`
- `output/{job_id}/parsed_filters.json`
- `output/{job_id}/parsed_parameters.json`

**State Updated:**
- `parsed_dashboards`
- `parsed_worksheets`
- `parsed_datasources`
- `parsed_calculations`
- `parsed_filters` (NEW)
- `parsed_parameters` (NEW)

## Benefits

- **Lightweight:** No LLM calls, just XML parsing
- **Complete:** All component types with structure
- **Structured:** Features + structure for complexity analysis
- **Report-ready:** Data structure supports HTML report generation
- **Platform agnostic:** Uses parsing_instructions from Exploration Agent

## Integration

### Complexity Analysis Agents
- Use `parsed_*` data with structure
- Analyze features AND structure for complexity
- Use dependencies for relationship analysis

### Strategy Agent (HTML Report)
- Use `parsed_dashboards` for dashboard complexity
- Use `parsed_worksheets` for visualization complexity
- Use `parsed_datasources` for data source support analysis
- Use `parsed_filters` and `parsed_parameters` for interactivity analysis
- Use structure for detailed breakdowns

## Edge Cases

1. **Missing file:** Skip component, log warning
2. **Invalid XML:** Catch exception, skip component
3. **Missing parsing_instructions:** Use default extraction logic
4. **Missing structure:** Extract basic structure, log warning
5. **Circular dependencies:** Handle gracefully, log warning

## Testing Strategy

1. **Unit Test:** Test each parsing function with sample XML
2. **Integration Test:** Test with real Tableau file
3. **Structure Test:** Verify structure capture for all component types
4. **Dependency Test:** Verify dependency extraction
5. **Full Workflow Test:** File Analysis → Exploration → Parsing

