"""Agent prompts for schema design and transformation"""

SCHEMA_DESIGN_PROMPT = """You are a PostgreSQL database schema designer.

Your task: Design a normalized relational schema from the analyzed JSON hierarchy.

INPUT:
{hierarchy}

RULES:
1. **Table Naming**: Use singular names (dashboard, not dashboards)

2. **Parent Entities (Level 1-2)**: Create simple tables with:
   - Primary key: <entity_name>_id SERIAL PRIMARY KEY
   - Basic metadata columns based on common fields
   - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

3. **Child Entities (Level 3+)**: Use sample_data to design columns:
   - Infer data types from samples:
     * Numbers → INTEGER or NUMERIC
     * Text → VARCHAR(255) or TEXT
     * true/false → BOOLEAN
     * Dates → TIMESTAMP
     * Complex structures → JSONB
   - Add foreign key to parent: <parent_name>_id INTEGER REFERENCES <parent_table>(<parent_name>_id)

4. **Data Types**:
   - Short text (< 255 chars) → VARCHAR(255)
   - Long text → TEXT
   - Whole numbers → INTEGER
   - Decimals → NUMERIC(10,2)
   - Dates/times → TIMESTAMP
   - Boolean → BOOLEAN
   - Complex/variable → JSONB

5. **Relationships**: Add foreign key constraints for all parent-child relationships

OUTPUT FORMAT (JSON):
{{
  "tables": [
    {{
      "table_name": "workbook",
      "ddl": "CREATE TABLE IF NOT EXISTS workbook (workbook_id SERIAL PRIMARY KEY, workbook_name VARCHAR(255), version VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
    }},
    {{
      "table_name": "dashboard",
      "ddl": "CREATE TABLE IF NOT EXISTS dashboard (dashboard_id SERIAL PRIMARY KEY, workbook_id INTEGER REFERENCES workbook(workbook_id), dashboard_name VARCHAR(255), zone_count INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
    }}
  ],
  "indexes": [
    "CREATE INDEX IF NOT EXISTS idx_dashboard_workbook ON dashboard(workbook_id);"
  ]
}}

CRITICAL REQUIREMENTS:
1. **Complete JSON**: Your response MUST be complete, valid JSON. Do NOT truncate mid-string or mid-object.
2. **Response Length**: If the schema is very large, prioritize the most important tables (workbook, datasource, worksheet, dashboard, and their direct children).
3. **JSON Format**: Return ONLY the JSON object, wrapped in ```json code blocks. Ensure all strings are properly closed.
4. **Validation**: Before returning, verify your JSON is complete and can be parsed.

Generate complete DDL statements. Return ONLY valid JSON wrapped in ```json code blocks, no markdown or explanations outside the code block.
"""

TRANSFORMATION_SQL_PROMPT = """You are a PostgreSQL SQL expert specializing in JSONB data transformation.

Your task: Generate SQL queries to transform JSONB data from raw_tableau_files into relational tables.

INPUT:
Schema: {schema}
Hierarchy: {hierarchy}

For each table, generate an INSERT statement that:
1. Extracts data from raw_tableau_files.raw_json using JSONB operators
2. Uses appropriate JSONB functions:
   - `->` for object navigation (returns JSONB)
   - `->>` for text extraction (returns TEXT)
   - `jsonb_array_elements()` for arrays
   - `jsonb_array_length()` for array counts
   - `::INTEGER`, `::BOOLEAN` for type casting

3. Handles parent-child relationships:
   - Store parent ID using RETURNING clause
   - Use placeholder :parent_table_id for foreign keys

POSTGRESQL JSONB FUNCTIONS:
- `raw_json->>'field'` - Get text value
- `raw_json->'field'` - Get JSONB value
- `jsonb_array_elements(raw_json->'array_field')` - Expand array
- `jsonb_array_length(raw_json->'array_field')` - Array length
- `(raw_json->>'numeric_field')::INTEGER` - Cast to integer

OUTPUT FORMAT (JSON):
{{
  "transformations": [
    {{
      "table_name": "workbook",
      "order": 1,
      "sql": "INSERT INTO workbook (workbook_name, version) SELECT raw_json->>'name', raw_json->>'version' FROM raw_tableau_files WHERE id = :file_id RETURNING workbook_id;"
    }},
    {{
      "table_name": "dashboard",
      "order": 2,
      "sql": "INSERT INTO dashboard (workbook_id, dashboard_name) SELECT :workbook_id, dashboard->>'name' FROM raw_tableau_files, jsonb_array_elements(raw_json->'dashboards') as dashboard WHERE id = :file_id RETURNING dashboard_id;"
    }},
    {{
      "table_name": "zone",
      "order": 3,
      "sql": "INSERT INTO zone (dashboard_id, zone_name, x_position, y_position) SELECT d.dashboard_id, zone->>'name', (zone->>'x')::INTEGER, (zone->>'y')::INTEGER FROM raw_tableau_files r, jsonb_array_elements(r.raw_json->'dashboards') as dashboard, jsonb_array_elements(dashboard->'zones') as zone JOIN dashboard d ON d.dashboard_name = dashboard->>'name' WHERE r.id = :file_id;"
    }}
  ]
}}

Generate SQL that can be executed in order. Use :file_id and :parent_table_id placeholders.
Return ONLY valid JSON, no markdown.
"""
