# Tableau to Looker Migration Prompts

This directory contains prompts for converting Tableau metadata to Looker LookML through a two-stage process:

1. **DSL Generation**: Extract Tableau metadata into Compact DSL format
2. **LookML Generation**: Convert DSL into Looker LookML code

## Directory Structure

```
prompts/
├── dsl_generation/          # Prompts for generating DSL from Tableau metadata
│   ├── connection.txt      # Extract connection information → Connection DSL
│   ├── fields.txt          # Extract field definitions → Field DSL
│   ├── worksheet.txt       # Extract worksheet definitions → Worksheet DSL
│   └── dashboard.txt       # Extract dashboard definitions → Dashboard DSL
│
└── lookml_generation/      # Prompts for generating LookML from DSL
    ├── connection_to_lookml.txt  # Connection DSL → LookML model file
    ├── fields_to_lookml.txt      # Field DSL → LookML view files
    ├── worksheet_to_lookml.txt   # Worksheet DSL → LookML explore definitions
    └── dashboard_to_lookml.txt   # Dashboard DSL → LookML dashboard files
```

## Workflow

### Stage 1: DSL Generation (TWB → DSL)

1. **Connection Extraction** (`dsl_generation/connection.txt`)
   - Input: Connection chunk JSON from TWB file
   - Output: Connection DSL with datasource, connection type, tables, and joins

2. **Field Extraction** (`dsl_generation/fields.txt`)
   - Input: Field chunk JSON from TWB file
   - Output: Field DSL with dimensions, measures, and calculated fields
   - Includes table inference for calculated fields

3. **Worksheet Extraction** (`dsl_generation/worksheet.txt`)
   - Input: Worksheet batch chunk JSON
   - Output: Worksheet DSL with rows, columns, marks, and filters
   - Handles batched worksheets with datasource chunk references

4. **Dashboard Extraction** (`dsl_generation/dashboard.txt`)
   - Input: Dashboard batch chunk JSON
   - Output: Dashboard DSL with layout, zones, worksheets, and filters
   - Handles batched dashboards with datasource chunk references

### Stage 2: LookML Generation (DSL → LookML)

1. **Model Generation** (`lookml_generation/connection_to_lookml.txt`)
   - Input: Connection DSL
   - Output: LookML model file with connection setup

2. **View Generation** (`lookml_generation/fields_to_lookml.txt`)
   - Input: Field DSL
   - Output: LookML view files (one per table)
   - Converts Tableau formulas to target SQL dialect
   - Handles dimensions, measures, and calculated fields

3. **Explore Generation** (`lookml_generation/worksheet_to_lookml.txt`)
   - Input: Worksheet DSL
   - Output: LookML explore definitions in model file
   - Maps worksheets to explores with filters and field selections

4. **Dashboard Generation** (`lookml_generation/dashboard_to_lookml.txt`)
   - Input: Dashboard DSL
   - Output: LookML dashboard files
   - Converts Tableau dashboard layout to Looker dashboard structure

## Usage

### DSL Generation

Use prompts from `dsl_generation/` with Tableau metadata chunks:

```python
# Example: Generate Field DSL
with open('prompts/dsl_generation/fields.txt') as f:
    prompt = f.read()
    
# Use with field chunk JSON
dsl_output = llm.generate(prompt + field_chunk_json)
```

### LookML Generation

Use prompts from `lookml_generation/` with generated DSL:

```python
# Example: Generate LookML Views
with open('prompts/lookml_generation/fields_to_lookml.txt') as f:
    prompt = f.read()
    
# Use with field DSL
lookml_output = llm.generate(prompt + field_dsl)
```

## Key Features

### DSL Generation Prompts

- **Batched Processing**: Worksheets and dashboards are processed in batches to reduce API calls
- **Table Inference**: Calculated fields automatically infer their source tables
- **Field Reference Mapping**: Cleans and maps Tableau field references to DSL format
- **Multi-table Support**: Handles calculated fields that reference multiple tables

### LookML Generation Prompts

- **SQL Dialect Conversion**: Automatically converts Tableau formulas to target SQL dialect (BigQuery, Snowflake, Redshift, etc.)
- **Type Mapping**: Maps Tableau data types to Looker types
- **Filter Conversion**: Converts Tableau filters to LookML filters
- **Layout Preservation**: Attempts to preserve dashboard layout structure

## Prompt Variables

All prompts use consistent variable naming:

- `CONNECTION_PROMPT` / `CONNECTION_DSL_TO_LOOKML_PROMPT`
- `FIELD_CHUNK_PROMPT` / `FIELDS_DSL_TO_LOOKML_PROMPT`
- `WORKSHEET_CHUNK_PROMPT` / `WORKSHEET_DSL_TO_LOOKML_PROMPT`
- `DASHBOARD_CHUNK_PROMPT` / `DASHBOARD_DSL_TO_LOOKML_PROMPT`

## Notes

- All prompts are designed to work with GenAI models (GPT-4, Claude, etc.)
- Prompts include extensive examples and validation checklists
- SQL dialect conversion is automatic based on connection type
- Layout conversion from Tableau to Looker is approximate due to different coordinate systems

