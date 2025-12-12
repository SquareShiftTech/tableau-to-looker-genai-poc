# Exploration Agent - Component Discovery & Index Creation Design

## Problem

After File Analysis Agent splits files, we need to:
1. Discover what components exist in the split files
2. Identify what features to extract for each component
3. Create a "book index" that guides Parsing Agent on how to extract features
4. Support multiple BI platforms (Tableau, Cognos, Power BI, etc.)

## Solution

**Exploration Agent = Discovery + Index Creation**

Use LLM to:
1. Discover components from each file (id, name, type, location)
2. Identify features to extract (using feature catalog to prevent hallucination)
3. Generate parsing instructions per component
4. Create comprehensive index/catalog for downstream agents

## Design

### Flow

```
1. Get all files from parsed_elements_paths (all ≤500KB from File Analysis Agent)
2. Get platform from state (tableau, cognos, power_bi, etc.)
3. Load feature catalog from config/feature_catalog.json
4. For each file:
   ├─ Read XML content
   ├─ Call LLM to discover:
   │   ├─ Components (id, name, type)
   │   ├─ Features to extract (reference feature catalog)
   │   └─ Parsing instructions
   └─ Store results
5. Merge results by component type
6. Build relationships (dashboard → worksheets, etc.)
7. Output: Component index/catalog
```

### LLM Discovery Process

**One LLM call per file:**
- Input: XML content + feature catalog + platform
- Output: Discovered components with features and parsing instructions

**Feature Catalog Usage:**
- LLM references existing features to prevent hallucination
- Only adds new features if discovered in XML
- Maintains consistency across runs

## Implementation

### 1. Feature Catalog

**File:** `config/feature_catalog.json`

```json
{
  "tableau": {
    "dashboard": {
      "standard_features": [
        "filters",
        "worksheets_used",
        "interactivity",
        "layout",
        "parameters"
      ]
    },
    "worksheet": {
      "standard_features": [
        "chart_type",
        "data_fields",
        "filters",
        "calculations",
        "interactivity"
      ]
    },
    "datasource": {
      "standard_features": [
        "connection_type",
        "tables",
        "fields",
        "connection_string"
      ]
    },
    "calculation": {
      "standard_features": [
        "formula",
        "data_type",
        "aggregation"
      ]
    }
  },
  "cognos": {
    "report": {
      "standard_features": [...]
    }
  },
  "power_bi": {
    "report": {
      "standard_features": [...]
    }
  }
}
```

### 2. New LLM Service Method

**File:** `services/llm_service.py`

```python
async def discover_components_from_file(
    self,
    file_path: str,
    file_content: str,
    platform: str,
    feature_catalog: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Discover components from a single file using LLM.
    
    Args:
        file_path: Path to the file
        file_content: XML content of the file
        platform: BI platform (tableau, cognos, etc.)
        feature_catalog: Feature catalog for the platform
    
    Returns:
        Dict with discovered components, features, and parsing instructions
    """
    # Build prompt with:
    # - XML content
    # - Platform context
    # - Feature catalog (to prevent hallucination)
    # - Instructions to discover components and features
    
    # Call LLM
    # Parse response
    # Return structured output
```

### 3. Exploration Agent Updates

**File:** `agents/exploration_agent.py`

**Changes:**
```python
async def exploration_agent(state: AssessmentState) -> AssessmentState:
    # 1. Get files and platform
    parsed_elements_paths = state.get('parsed_elements_paths', [])
    platform = state.get('source_files', [])[0].get('platform', 'tableau')
    
    # 2. Load feature catalog
    feature_catalog = load_feature_catalog(platform)
    
    # 3. Process each file with LLM
    all_discoveries = []
    for file_info in parsed_elements_paths:
        file_path = file_info.get('file_path')
        file_content = read_file(file_path)
        
        discovery = await llm_service.discover_components_from_file(
            file_path, file_content, platform, feature_catalog
        )
        all_discoveries.append(discovery)
    
    # 4. Merge discoveries by component type
    merged_catalog = merge_discoveries(all_discoveries)
    
    # 5. Build relationships
    relationships = build_relationships(merged_catalog)
    
    # 6. Create final index
    component_index = {
        "platform": platform,
        "components": merged_catalog,
        "feature_catalog": feature_catalog,
        "relationships": relationships
    }
    
    # 7. Save to JSON file
    save_index(component_index, output_dir)
    
    # 8. Update state
    state['discovered_components'] = component_index
    return state
```

### 4. Output Structure

**File:** `output/{job_id}/discovered_components.json`

```json
{
  "platform": "tableau",
  "discovery_metadata": {
    "total_files_processed": 52,
    "discovery_timestamp": "2025-01-11T10:30:00Z"
  },
  "components": {
    "dashboards": [
      {
        "id": "dashboard-1",
        "name": "Sales Dashboard",
        "file": "output/job_id/dashboard_1.xml",
        "features_to_extract": [
          "filters",
          "worksheets_used",
          "interactivity",
          "layout",
          "parameters"
        ],
        "parsing_instructions": {
          "filters": "Extract all <filter> elements within <dashboard>",
          "worksheets_used": "Find <worksheet> references in <zone> elements",
          "interactivity": "Check for <action> elements and their types",
          "layout": "Extract <zone> structure and positioning",
          "parameters": "Find <parameter> references used in dashboard"
        }
      }
    ],
    "worksheets": [
      {
        "id": "sheet-1",
        "name": "Sales by Region",
        "file": "output/job_id/worksheet_1.xml",
        "features_to_extract": [
          "chart_type",
          "data_fields",
          "filters",
          "calculations",
          "interactivity"
        ],
        "parsing_instructions": {
          "chart_type": "Extract <view> element's type attribute",
          "data_fields": "Find all <column> elements in <columns> section",
          "filters": "Extract <filter> elements and their expressions",
          "calculations": "Find <calculation> elements with formula attributes",
          "interactivity": "Check for <action> elements"
        }
      }
    ],
    "datasources": [
      {
        "id": "ds-1",
        "name": "Sales Database",
        "file": "output/job_id/datasource_1.xml",
        "features_to_extract": [
          "connection_type",
          "tables",
          "fields",
          "connection_string"
        ],
        "parsing_instructions": {
          "connection_type": "Extract <connection> element's class attribute",
          "tables": "Find all <table> elements and their names",
          "fields": "Extract <column> elements with name and type",
          "connection_string": "Extract <connection> element's server, dbname attributes"
        }
      }
    ],
    "calculations": [
      {
        "id": "calc-1",
        "name": "Profit Margin",
        "file": "output/job_id/datasource_1.xml",
        "datasource_id": "ds-1",
        "features_to_extract": [
          "formula",
          "data_type",
          "aggregation"
        ],
        "parsing_instructions": {
          "formula": "Extract <calculation> element's formula attribute",
          "data_type": "Get <column> element's type attribute",
          "aggregation": "Check if formula contains aggregation functions"
        }
      }
    ]
  },
  "feature_catalog": {
    "dashboard": {
      "standard_features": ["filters", "worksheets_used", "interactivity", "layout", "parameters"],
      "new_features_discovered": []
    },
    "worksheet": {
      "standard_features": ["chart_type", "data_fields", "filters", "calculations", "interactivity"],
      "new_features_discovered": []
    },
    "datasource": {
      "standard_features": ["connection_type", "tables", "fields", "connection_string"],
      "new_features_discovered": []
    },
    "calculation": {
      "standard_features": ["formula", "data_type", "aggregation"],
      "new_features_discovered": []
    }
  },
  "relationships": [
    {
      "type": "dashboard_uses_worksheet",
      "from": "dashboard-1",
      "to": ["sheet-1", "sheet-2"]
    },
    {
      "type": "worksheet_uses_datasource",
      "from": "sheet-1",
      "to": ["ds-1"]
    },
    {
      "type": "calculation_belongs_to_datasource",
      "from": "calc-1",
      "to": ["ds-1"]
    }
  ]
}
```

## LLM Prompt Design

### Prompt Structure

```
You are analyzing a {platform} metadata file to discover components and identify features.

File Content:
{file_content}

Known Features (use these to prevent hallucination):
{feature_catalog}

Task:
1. Discover all components in this file (dashboards, worksheets, datasources, calculations, etc.)
2. For each component:
   - Extract: id, name, type
   - Identify features to extract (use known features from catalog, add new ones only if found)
   - Generate parsing instructions (how to extract each feature from XML)
3. Identify relationships between components

Return JSON:
{
  "components": {
    "dashboards": [...],
    "worksheets": [...],
    "datasources": [...],
    "calculations": [...]
  },
  "new_features_discovered": [...],
  "relationships": [...]
}
```

## Edge Cases

1. **Empty file:** Skip, log warning
2. **No components found:** Return empty structure
3. **Invalid XML:** Catch exception, skip file
4. **Feature catalog missing:** Use empty catalog, log warning
5. **LLM timeout/error:** Retry with exponential backoff, skip if fails
6. **Platform not in catalog:** Use generic features, log warning

## Benefits

- **Platform agnostic:** Works for any BI platform
- **Prevents hallucination:** Uses feature catalog as reference
- **Comprehensive:** Discovers components, features, and relationships
- **Guides parsing:** Provides instructions for Parsing Agent
- **Supports reporting:** Index feeds into final report generation

## Integration with Downstream Agents

### Parsing Agent
- Uses `discovered_components` from state
- Reads `parsing_instructions` for each component
- Extracts detailed features using instructions

### Complexity Analysis Agents
- Use `components` catalog to analyze each component
- Use `features_to_extract` to assess complexity
- Use `relationships` to understand dependencies

### Strategy Agent
- Uses `components` for inventory summary
- Uses `feature_catalog` for complexity analysis
- Uses `relationships` for dependency mapping
- Generates final HTML report

## Configuration

- **Feature Catalog:** `config/feature_catalog.json` (JSON file)
- **LLM Settings:** Uses existing `chunk_max_size_bytes` (500KB default)
- **Retry Logic:** Uses existing retry mechanism from `llm_service.py`

## Testing Strategy

1. **Unit Test:** Test LLM discovery with sample XML
2. **Integration Test:** Test with real Tableau file
3. **Multi-platform Test:** Test with Cognos, Power BI files
4. **Feature Catalog Test:** Verify hallucination prevention
5. **Relationship Test:** Verify relationship discovery
6. **Full Workflow Test:** File Analysis → Exploration → Parsing

