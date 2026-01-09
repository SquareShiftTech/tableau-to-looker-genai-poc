import json
import re
from typing import TypedDict, Dict, Any, List
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

# ============================================================================
# 1. CONFIGURATION
# ============================================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "tableau_migration",
    "user": "roobar",
    "password": "postgres",
}
password = quote_plus(DB_CONFIG["password"])
DATABASE_URI = (
    f"postgresql://{DB_CONFIG['user']}:{password}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

engine = create_engine(DATABASE_URI)

# LLM (LLM does scoring based on rules in the prompt)
llm = ChatVertexAI(model="gemini-2.0-flash-001", temperature=0)

# ============================================================================
# 2. PROMPTS FOR SPECIALIZED AGENTS
# ============================================================================

FIELD_AGENT_PROMPT = """
You are a highly strict **Tableau Field Logic Analyzer** for **Tableau to Looker Migration Assessment**.  
You MUST output JSON only. No explanations before or after. No markdown.

---------------------------------------------------------------------
### CONTEXT: TABLEAU TO LOOKER MIGRATION

You are analyzing Tableau workbooks to assess migration complexity to Looker (Google Cloud's BI platform).
The complexity scores reflect how difficult it will be to migrate each component from Tableau to Looker.

**Why these scores matter for Looker migration:**
- **LOD (Level of Detail) expressions** are complex in Tableau and require careful translation to Looker's equivalent (table calculations or derived tables)
- **Table Calculations** in Tableau map to Looker table calculations but require different syntax and logic
- **Date Functions** need conversion from Tableau's date functions to Looker's date functions
- **Aggregations** are generally straightforward but still require mapping
- **Arithmetic/Logic** formulas need syntax conversion
- **Parameters** in Tableau need to be converted to Looker filters or parameters

Your scoring should reflect the **migration effort** required, not just generic complexity.

---------------------------------------------------------------------
### YOUR INPUT
You will receive:
{
  "datasources": [...],
  "fields": [...],
  "parameters": [...]
}

Each field has:
- id
- datasource_id
- caption
- internal_name
- formula (string or null)
- data_type
- role
- is_calculated (true/false)

---------------------------------------------------------------------
### YOUR JOB
For EACH field:
1. Inspect its `formula`.
2. Determine EXACTLY ONE primary complexity driver from this set:
   - "LOD"
   - "Table Calculation"
   - "Date Function"
   - "Aggregation"
   - "Arithmetic / Logic"
   - "Simple"
   - "None"

3. Assign EXACT score based on these **strict, numeric rules for Tableau to Looker migration complexity**:

| Complexity Driver      | Score | Migration Challenge to Looker |
|----------------------|--------|------------------------------|
| LOD                  | 10     | LOD expressions require complex translation to Looker table calculations or derived tables |
| Table Calculation    | 5      | Table calculations need syntax conversion and logic restructuring for Looker |
| Date Function        | 2      | Date functions need conversion from Tableau syntax to Looker date functions |
| Aggregation          | 1      | Aggregations are straightforward but still require mapping to Looker |
| Arithmetic / Logic   | 1      | Formulas need syntax conversion from Tableau to Looker expression language |
| Simple               | 0      | Simple formulas are easy to migrate |
| None (no formula)    | 0      | No migration complexity for non-calculated fields |

4. A formula matches these categories STRICTLY:

- LOD → Contains `{ FIXED`, `{INCLUDE`, `{ EXCLUDE`
- Table Calculation → Contains LOOKUP, WINDOW_, RUNNING_, INDEX, RANK(
- Date Function → Contains DATEADD, DATEPART, DATETRUNC, DATE(, YEAR(, MONTH(
- Aggregation → Contains SUM( or AVG(
- Arithmetic / Logic → Contains IF, CASE, +, -, *, /
- Simple → has formula but none of above rules matched
- None → formula is null AND is_calculated = false

5. For each **datasource**, compute:
   complexity_score = SUM(all field scores)

6. For each parameter:
   score = 5
   * **Why**: Tableau parameters need to be converted to Looker filters or parameters, requiring migration effort

---------------------------------------------------------------------
### OUTPUT RULES (VERY STRICT)

You MUST output ONLY JSON between `<JSON>` and `</JSON>` tags.

The JSON MUST match this schema exactly:

{
  "datasources": [
    {
      "id": "string",
      "name": "string or null",
      "caption": "string or null",
      "complexity_score": number,
      "fields": [
        {
          "id": "string",
          "name": "string",
          "data_type": "string or null",
          "role": "string or null",
          "is_calculated": boolean,
          "formula": "string or null",
          "complexity_drivers": "LOD | Table Calculation | Date Function | Aggregation | Arithmetic / Logic | Simple | None",
          "score": number
        }
      ]
    }
  ],
  "parameters": [
    {
      "id": "string",
      "name": "string",
      "data_type": "string or null",
      "default_value": "string or null",
      "score": 5
    }
  ]
}

---------------------------------------------------------------------
### IMPORTANT RULES
- You must NEVER add keys not listed in the schema.
- You must NEVER omit keys.
- If value missing → output null.
- Never reorder top-level keys.
- Never wrap JSON in markdown.
- Output JSON ONLY.

---------------------------------------------------------------------
Return final answer as:

<JSON>
{ ... }
</JSON>
"""

VIZ_AGENT_PROMPT = """
You are a strict **Tableau Visualization Analyzer** for **Tableau to Looker Migration Assessment**.  
Output JSON only. No markdown. No explanation.

---------------------------------------------------------------------
### CONTEXT: TABLEAU TO LOOKER MIGRATION

You are analyzing Tableau visualizations to assess migration complexity to Looker (Google Cloud's BI platform).
The complexity scores reflect how difficult it will be to recreate each visualization type in Looker.

**Why visualization types matter for Looker migration:**
- **Complex visualizations** (heatmap, gantt, path, polygon) are harder to recreate in Looker and may require custom visualizations or workarounds
- **Maps** require different geographic data handling in Looker
- **Simple charts** (bar, line, pie) are straightforward to migrate
- **Dual-axis charts** add complexity as Looker handles multiple measures differently
- **Field complexity** (LOD, table calculations) compounds visualization complexity

Your scoring should reflect the **migration effort** required to recreate the visualization in Looker, not just generic complexity.

---------------------------------------------------------------------
### INPUT
{
  "worksheets": [...],
  "worksheet_elements": [...],
  "fields": [...]  // Fields from datasources used by worksheets
}

Each worksheet_element has:
- worksheet_id
- mark_class (string)
- pane_id
- element_type
- encoding
- style

Each field has:
- id
- datasource_id
- name/caption
- formula
- complexity_drivers (LOD, Table Calculation, Date Function, etc.)
- score (from field analysis)

---------------------------------------------------------------------
### SCORING RULES

**Step 1: Calculate Visualization Score (viz_score) for Tableau to Looker Migration**

Base score by viz type (reflecting migration difficulty to Looker):

| Viz Type   | Score | Migration Challenge to Looker |
|------------|--------|------------------------------|
| bar        | 1     | Easy - standard chart type in Looker |
| line       | 1     | Easy - standard chart type in Looker |
| area       | 1     | Easy - standard chart type in Looker |
| pie        | 1     | Easy - standard chart type in Looker |
| text       | 1     | Easy - text tiles in Looker |
| scatter    | 1     | Easy - scatter plot in Looker |
| map        | 3     | Moderate - requires geographic data setup in Looker |
| polygon    | 8     | Complex - may require custom visualization or workaround |
| heatmap    | 10    | Complex - difficult to recreate exactly in Looker |
| gantt      | 10    | Complex - may require custom visualization in Looker |
| path       | 10    | Complex - difficult to recreate in Looker's standard charts |
| none       | 0     | No visualization complexity |

PRIMARY viz type = the mark_class with HIGHEST score.

Dual-axis = true IF:
- Any mark_class in {bar, line, area} appears MORE THAN ONCE inside same worksheet.

viz_score = base_chart_score + 3 IF dual-axis = true

**Step 2: Calculate Field Score (field_score)**

For each worksheet:
1. Find all fields from the worksheet's datasource_id
2. Sum the field scores: field_score = SUM(all field scores for that datasource)

**Step 3: Calculate Combined Complexity Score**

complexity_score = viz_score + field_score

This represents the TOTAL complexity of the worksheet (both visualization type AND the complexity of fields used).

---------------------------------------------------------------------
### OUTPUT JSON SCHEMA (STRICT)

You MUST return:

<JSON>
{
  "worksheets": [
    {
      "id": "string",
      "name": "string",
      "datasource_id": "string or null",
      "viz_type": "string",
      "mark_classes": ["string"],
      "dual_axis": boolean,
      "viz_score": number,
      "field_score": number,
      "complexity_score": number,
      "fields": [
        {
          "id": "string",
          "name": "string",
          "formula": "string or null",
          "complexity_drivers": "string or null",
          "score": number
        }
      ]
    }
  ]
}
</JSON>

Rules:
- Never omit keys.
- mark_classes must be a deduped list.
- viz_type must be lowercase.
- fields array should contain all fields from the worksheet's datasource.
- complexity_score = viz_score + field_score
- If no elements exist → viz_type="none", dual_axis=false, viz_score=0.
- If no fields found → field_score=0, fields=[].
"""

LAYOUT_AGENT_PROMPT = """
You are a strict **Tableau Dashboard Layout Analyzer** for **Tableau to Looker Migration Assessment**.  
Output JSON ONLY between <JSON> and </JSON>.

---------------------------------------------------------------------
### CONTEXT: TABLEAU TO LOOKER MIGRATION

You are analyzing Tableau dashboard layouts to assess migration complexity to Looker (Google Cloud's BI platform).
The complexity scores reflect how difficult it will be to recreate the dashboard layout and structure in Looker.

**Why dashboard layout matters for Looker migration:**
- **Floating objects** in Tableau are difficult to replicate in Looker's grid-based layout system
- **Tiled layouts** are easier to migrate as Looker uses a similar grid system
- **High component counts** require more manual work to recreate in Looker dashboards
- **Complex zone structures** may need restructuring for Looker's layout constraints

Your scoring should reflect the **migration effort** required to recreate the dashboard layout in Looker, not just generic complexity.

---------------------------------------------------------------------
### INPUT
{
  "dashboards": [...]
}

Each dashboard:
- id
- name
- width
- height
- zones (null OR JSON array or string containing JSON)

Each zone may include:
- floating or is_floating (boolean)
- worksheet OR worksheet_id (sheet reference)
- type

---------------------------------------------------------------------
### SCORING RULES FOR TABLEAU TO LOOKER MIGRATION

Start with:
layout_score = 0 if zones = null or empty  
layout_score = 1 if zones exist AND count ≥ 1

Then (reflecting migration difficulty to Looker):
- If ANY zone has floating=true → add +8  
  * **Why**: Floating objects are very difficult to replicate in Looker's grid-based layout system
- If number_of_zones > 15 → add +5
  * **Why**: High component counts require significant manual work to recreate in Looker dashboards  

You MUST compute:
- is_floating
- floating_count
- component_count
- contained_sheet_ids = list of worksheet IDs referenced

---------------------------------------------------------------------
### OUTPUT JSON SCHEMA

<JSON>
{
  "dashboards": [
    {
      "id": "string",
      "name": "string",
      "width": number or null,
      "height": number or null,
      "is_floating": boolean,
      "floating_count": number,
      "component_count": number,
      "contained_sheet_ids": ["string"],
      "layout_score": number
    }
  ]
}
</JSON>

Rules:
- Never omit keys.
- If no zones → contained_sheet_ids=[], component_count=0.
- Never wrap in markdown.
"""

HTML_AGENT_PROMPT = """
You are a **Professional HTML Report Generator** for **Tableau to Looker Migration Assessment**.

Your task is to convert a JSON complexity analysis report into a beautiful, professional HTML report that matches the exact style of the reference design.

**CONTEXT**: This report assesses the complexity of migrating Tableau workbooks to Looker (Google Cloud's BI platform). 
All complexity scores reflect the effort and difficulty required for this specific migration, not generic complexity.

---------------------------------------------------------------------
### INPUT JSON STRUCTURE

{
  "workbook": {
    "name": "string",
    "id": "string",
    "summary": {
      "total_complexity_score": number,
      "worksheet_score": number,
      "worksheet_viz_score": number,
      "worksheet_field_score": number,
      "datasource_field_score": number,
      "layout_score": number,
      "parameter_score": number,
      "migration_category": "Low | Medium | High"
    },
    "datasources": [...],
    "parameters": [...],
    "worksheets": [...],
    "dashboards": [...],
    "validation": {
      "field_agent": {
        "valid": boolean,
        "error_count": number,
        "warning_count": number
      },
      "viz_agent": {
        "valid": boolean,
        "error_count": number,
        "warning_count": number
      },
      "layout_agent": {
        "valid": boolean,
        "error_count": number,
        "warning_count": number
      }
    }
  }
}

---------------------------------------------------------------------
### HTML REQUIREMENTS - EXACT STYLE MATCH

1. **CSS Styling** (MUST match reference exactly):
   - Use 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif font family
   - Background: #f4f4f4 for body, #fff for container
   - Header h1 color: #007bff
   - Section h2 color: #007bff with border-bottom
   - Table headers: #f8f9fa background
   - Alternating row colors: #f8f9fa for even rows
   - Hover effect on table rows: #e9ecef background

2. **Summary Cards**:
   - Display as flex cards with border, padding, border-radius
   - Width: 250px each
   - Show: Total Complexity Score, Worksheet Score, Datasource Field Score, Migration Category
   - Migration Category badge: .badge.low (green), .badge.medium (orange), .badge.high (red)

3. **VALIDATION STATUS SECTION** (CRITICAL - Add this after summary):
   - Create a section with class "validation"
   - Display validation results in a clean table or cards
   - Show for each agent: field_agent, viz_agent, layout_agent
   - Display: Status (✅ PASSED / ❌ FAILED), Error Count, Warning Count
   - Use green badge for "valid: true", red badge for "valid: false"
   - Style it consistently with the rest of the report

4. **Datasources Table** (EXACT format):
   - Columns: Name, Caption, Complexity Score, Complexity Drivers
   - NO nested tables, NO field details
   - Complexity Drivers: Show as badge with class "complexity-driver" + type
   - Badge classes: .complexity-driver.lod (red), .complexity-driver.table-calculation (yellow), .complexity-driver.aggregation (blue), .complexity-driver.arithmetic (gray), .complexity-driver.none (green)
   - For each datasource, determine primary complexity driver from its fields (highest priority)

5. **Worksheets Table** (EXACT format):
   - Columns: Name, Viz Type, Complexity Score, Field, Formula, Complexity Drivers
   - Show the PRIMARY field used in the worksheet (first field or most complex)
   - Formula: Show the formula or "-" if null
   - **Complexity Drivers (CRITICAL LOGIC - MUST FOLLOW EXACTLY)**:
     * The complexity_score = viz_score + field_score
     * **NEVER show "None" if complexity_score > 0**
     * Determine the PRIMARY complexity driver using this priority:
     
     **Priority 1: If field_score > 0 AND field has complexity_drivers:**
       - Use the field's complexity_drivers (LOD, Table Calculation, Aggregation, Arithmetic / Logic, etc.)
       - This takes priority because field complexity is more specific
     
     **Priority 2: If viz_score > 0 AND field_score = 0:**
       - The complexity comes from the visualization type itself
       - Show the viz_type name capitalized as the complexity driver
       - Use badge class "complexity-driver viz-complex" (gray background #6c757d)
       - Examples:
         * heatmap → Show "Heatmap" with class "complexity-driver viz-complex"
         * gantt → Show "Gantt" with class "complexity-driver viz-complex"
         * polygon → Show "Polygon" with class "complexity-driver viz-complex"
         * map → Show "Map" with class "complexity-driver viz-complex"
         * bar, line, area, pie, text, scatter → If field_score=0, show viz_type name with "viz-complex" class
     
     **Priority 3: If both viz_score > 0 AND field_score > 0:**
       - Use the field's complexity_drivers (field complexity is more specific and actionable)
     
     **Priority 4: If both are 0:**
       - Show "None"
     
     **EXAMPLES:**
     * Worksheet with viz_score=10, field_score=0, complexity_score=10 → Show "Heatmap" or "Complex Viz" (NOT "None")
     * Worksheet with viz_score=1, field_score=1, complexity_score=2 → Show field's driver (e.g., "Aggregation")
     * Worksheet with viz_score=10, field_score=10, complexity_score=20 → Show field's driver (e.g., "LOD")
   - NO nested tables for fields

6. **Dashboards Table** (EXACT format):
   - Columns: Name, Component Count, Layout Score
   - Simple, clean table format

7. **Complexity Driver Badge Colors**:
   - LOD: #dc3545 (red) - class "complexity-driver lod"
   - Table Calculation: #ffc107 (yellow/orange) - class "complexity-driver table-calculation"
   - Date Function: #17a2b8 (blue) - class "complexity-driver date-function"
   - Aggregation: #007bff (blue) - class "complexity-driver aggregation"
   - Arithmetic / Logic: #6c757d (gray) - class "complexity-driver arithmetic"
   - None: #28a745 (green) - class "complexity-driver none"

8. **Footer**:
   - Simple centered footer with generation timestamp

---------------------------------------------------------------------
### EXACT HTML STRUCTURE TO FOLLOW

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tableau Migration Assessment Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
            color: #333;
        }
        .container {
            width: 90%;
            margin: 20px auto;
            background-color: #fff;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }
        header {
            text-align: center;
            padding: 20px 0;
            border-bottom: 1px solid #eee;
        }
        header h1 {
            color: #007bff;
            margin-bottom: 5px;
        }
        .summary {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .summary-card {
            background-color: #fff;
            border: 1px solid #eee;
            padding: 15px;
            margin: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
            width: 250px;
            text-align: center;
        }
        .summary-card h3 {
            margin-top: 0;
            margin-bottom: 10px;
            color: #555;
        }
        .badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            color: #fff;
        }
        .badge.low { background-color: #28a745; }
        .badge.medium { background-color: #ffc107; color: #212529; }
        .badge.high { background-color: #dc3545; }
        .badge.success { background-color: #28a745; }
        .badge.danger { background-color: #dc3545; }
        section {
            margin-bottom: 30px;
        }
        section h2 {
            color: #007bff;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background-color: #f8f9fa;
            font-weight: 600;
        }
        tbody tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        tbody tr:hover {
            background-color: #e9ecef;
        }
        .code {
            background-color: #f8f9fa;
            padding: 5px 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 0.9em;
        }
        .complexity-driver {
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 0.8em;
            color: #fff;
        }
        .complexity-driver.lod { background-color: #dc3545; }
        .complexity-driver.table-calculation { background-color: #ffc107; color: #212529; }
        .complexity-driver.date-function { background-color: #17a2b8; }
        .complexity-driver.aggregation { background-color: #007bff; }
        .complexity-driver.arithmetic { background-color: #6c757d; }
        .complexity-driver.none { background-color: #28a745; }
        .complexity-driver.viz-complex { background-color: #6c757d; }
        .validation {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .validation-item {
            margin-bottom: 10px;
        }
        footer {
            text-align: center;
            padding: 20px 0;
            border-top: 1px solid #eee;
            color: #777;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Tableau Migration Assessment Report</h1>
            <p>Workbook: {workbook_name} <span class="badge success">Database-Validated</span></p>
        </header>
        <section class="summary">
            <!-- Summary cards -->
        </section>
        <section class="validation">
            <!-- Validation status section -->
        </section>
        <section class="datasources">
            <!-- Datasources table -->
        </section>
        <section class="worksheets">
            <!-- Worksheets table -->
        </section>
        <section class="dashboards">
            <!-- Dashboards table -->
        </section>
        <footer>
            <p>Report generated on: {timestamp}</p>
        </footer>
    </div>
</body>
</html>

---------------------------------------------------------------------
### CRITICAL RULES

1. **Datasources**: Show ONLY Name, Caption, Complexity Score, Complexity Drivers (as badge)
2. **Worksheets**: Show Name, Viz Type, Complexity Score, Field (single field name), Formula (or "-"), Complexity Drivers (as badge)
3. **Dashboards**: Show Name, Component Count, Layout Score
4. **Validation**: Show status for each agent with badges
5. **NO nested tables** in Datasources or Worksheets sections
6. **Match the exact CSS styling** from the reference

---------------------------------------------------------------------
Generate the complete HTML report now. Return ONLY the HTML, nothing else.
"""

# ============================================================================
# 3. STATE DEFINITION
# ============================================================================

class MigrationState(TypedDict):
    workbook_name: str
    workbook_id: str

    # Partial Results
    field_data: Dict[str, Any]
    viz_data: Dict[str, Any]
    layout_data: Dict[str, Any]

    # Validation Results
    field_validation: Dict[str, Any]
    viz_validation: Dict[str, Any]
    layout_validation: Dict[str, Any]

    # Final Output
    final_report: Dict[str, Any]
    html_report: str


# ============================================================================
# 4. HELPERS
# ============================================================================

def convert_uuids(obj):
    """Recursively convert UUID objects to strings so JSON dump never breaks."""
    if isinstance(obj, dict):
        return {k: convert_uuids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_uuids(i) for i in obj]
    if hasattr(obj, "__class__") and obj.__class__.__name__ == "UUID":
        return str(obj)
    return obj


def run_query(sql: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Run SQL, return list of dicts with UUID already stringified."""
    params = params or {}
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = [convert_uuids(dict(row._mapping)) for row in result]
    return rows


def extract_json(text: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM output.

    1. Prefer JSON between <JSON>...</JSON>
    2. Fallback: first {...} block
    """
    # 1) Try <JSON>...</JSON> block
    try:
        m = re.search(r"<JSON>(.*?)</JSON>", text, re.DOTALL | re.IGNORECASE)
        if m:
            block = m.group(1).strip()
            return json.loads(block)
    except Exception:
        pass

    # 2) Fallback: first {...}
    try:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass

    return {}


def extract_html(text: str) -> str:
    """
    Extract HTML from LLM output.
    Removes markdown code blocks if present.
    """
    # Remove markdown code blocks
    text = re.sub(r"```html\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    
    # Try to find HTML content
    # Look for <!DOCTYPE or <html
    html_match = re.search(r"(<!DOCTYPE.*?</html>)", text, re.DOTALL | re.IGNORECASE)
    if html_match:
        return html_match.group(1)
    
    # Fallback: return the whole text if it looks like HTML
    if "<html" in text.lower() or "<!doctype" in text.lower():
        return text.strip()
    
    return text.strip()


# ============================================================================
# 5. NODE FUNCTIONS (AGENTS)
# ============================================================================

def setup_node(state: MigrationState):
    """Resolve workbook_id from workbooks table."""
    print(f"🔍 Resolving ID for: {state['workbook_name']}")
    rows = run_query(
        "SELECT id FROM workbooks WHERE name = :name LIMIT 1;",
        {"name": state["workbook_name"]},
    )
    wb_id = rows[0]["id"] if rows else None
    print(f"✅ Found ID: {wb_id}")
    return {"workbook_id": wb_id}


def field_agent_node(state: MigrationState):
    """LLM agent that scores datasources/fields/parameters based on formulas."""
    print("🤖 Running Field Logic Agent...")
    wb_id = state["workbook_id"]
    if not wb_id:
        return {"field_data": {}}

    datasources = run_query(
        """
        SELECT id, name, caption, connection_type, db_name, db_schema, is_extract
        FROM datasources
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

    fields = run_query(
        """
        SELECT f.id,
               f.datasource_id,
               f.caption,
               f.internal_name,
               f.formula,
               f.data_type,
               f.role,
               f.is_calculated
        FROM fields f
        JOIN datasources d ON d.id = f.datasource_id
        WHERE d.workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

    # parameters optional
    try:
        parameters = run_query(
            """
            SELECT id, workbook_id, name, data_type, default_value
            FROM parameters
            WHERE workbook_id = :wb;
            """,
            {"wb": wb_id},
        )
    except Exception:
        parameters = []

    payload = {
        "datasources": datasources,
        "fields": fields,
        "parameters": parameters,
    }

    # NOTE: no ```json fences; just raw JSON string
    prompt = (
        FIELD_AGENT_PROMPT
        + "\n\nRAW_DATA_JSON:\n"
        + json.dumps(payload, indent=2)
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    data = extract_json(response.content)
    return {"field_data": convert_uuids(data)}


def validate_field_agent_node(state: MigrationState):
    """
    Validator agent that verifies field_agent output against database.
    Checks for hallucinations and data accuracy.
    """
    print("🔍 Validating Field Agent Output...")
    wb_id = state["workbook_id"]
    field_data = state.get("field_data", {}) or {}
    
    if not wb_id or not field_data:
        return {"field_validation": {"valid": False, "errors": ["Missing workbook_id or field_data"]}}
    
    validation_errors = []
    validation_warnings = []
    corrected_data = {"datasources": [], "parameters": []}
    
    # Get actual data from database for comparison
    db_datasources = run_query(
        """
        SELECT id, name, caption, connection_type, db_name, db_schema, is_extract
        FROM datasources
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    db_fields = run_query(
        """
        SELECT f.id,
               f.datasource_id,
               f.caption,
               f.internal_name,
               f.formula,
               f.data_type,
               f.role,
               f.is_calculated
        FROM fields f
        JOIN datasources d ON d.id = f.datasource_id
        WHERE d.workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    try:
        db_parameters = run_query(
            """
            SELECT id, workbook_id, name, data_type, default_value
            FROM parameters
            WHERE workbook_id = :wb;
            """,
            {"wb": wb_id},
        )
    except Exception:
        db_parameters = []
    
    # Create lookup maps from database
    db_datasource_map = {str(ds["id"]): ds for ds in db_datasources}
    db_field_map = {str(f["id"]): f for f in db_fields}
    db_parameter_map = {str(p["id"]): p for p in db_parameters}
    
    # Validate datasources
    agent_datasources = field_data.get("datasources", [])
    for agent_ds in agent_datasources:
        ds_id = str(agent_ds.get("id", ""))
        
        if ds_id not in db_datasource_map:
            validation_errors.append(f"❌ HALLUCINATION: Datasource ID {ds_id} does not exist in database")
            continue
        
        db_ds = db_datasource_map[ds_id]
        validated_ds = {
            "id": ds_id,
            "name": db_ds.get("name"),  # Use DB value, not agent value
            "caption": db_ds.get("caption"),  # Use DB value
            "complexity_score": agent_ds.get("complexity_score", 0),  # Keep agent's score
            "fields": []
        }
        
        # Validate fields within this datasource
        agent_fields = agent_ds.get("fields", [])
        for agent_field in agent_fields:
            field_id = str(agent_field.get("id", ""))
            
            if field_id not in db_field_map:
                validation_errors.append(f"❌ HALLUCINATION: Field ID {field_id} does not exist in database")
                continue
            
            db_field = db_field_map[field_id]
            
            # Verify field belongs to this datasource
            if str(db_field.get("datasource_id")) != ds_id:
                validation_warnings.append(f"⚠️  Field {field_id} belongs to different datasource in DB")
                continue
            
            # Verify formula matches exactly
            agent_formula = agent_field.get("formula")
            db_formula = db_field.get("formula")
            
            if agent_formula != db_formula:
                validation_errors.append(
                    f"❌ FORMULA MISMATCH: Field {field_id} - Agent: '{agent_formula}' vs DB: '{db_formula}'"
                )
                # Use DB formula
                agent_field["formula"] = db_formula
            
            # Verify name/caption matches
            agent_name = agent_field.get("name")
            db_caption = db_field.get("caption")
            if agent_name != db_caption:
                validation_warnings.append(
                    f"⚠️  Field {field_id} name mismatch - Agent: '{agent_name}' vs DB: '{db_caption}'"
                )
                agent_field["name"] = db_caption  # Use DB value
            
            # Keep agent's complexity analysis but use DB data for facts
            validated_field = {
                "id": field_id,
                "name": db_caption,  # Use DB value
                "data_type": db_field.get("data_type"),
                "role": db_field.get("role"),
                "is_calculated": db_field.get("is_calculated"),
                "formula": db_formula,  # Use DB value
                "complexity_drivers": agent_field.get("complexity_drivers"),  # Keep agent's analysis
                "score": agent_field.get("score", 0)  # Keep agent's score
            }
            validated_ds["fields"].append(validated_field)
        
        corrected_data["datasources"].append(validated_ds)
    
    # Validate parameters
    agent_parameters = field_data.get("parameters", [])
    for agent_param in agent_parameters:
        param_id = str(agent_param.get("id", ""))
        
        if param_id not in db_parameter_map:
            validation_errors.append(f"❌ HALLUCINATION: Parameter ID {param_id} does not exist in database")
            continue
        
        db_param = db_parameter_map[param_id]
        
        # Verify name matches
        agent_name = agent_param.get("name")
        db_name = db_param.get("name")
        if agent_name != db_name:
            validation_warnings.append(
                f"⚠️  Parameter {param_id} name mismatch - Agent: '{agent_name}' vs DB: '{db_name}'"
            )
        
        validated_param = {
            "id": param_id,
            "name": db_name,  # Use DB value
            "data_type": db_param.get("data_type"),
            "default_value": db_param.get("default_value"),
            "score": agent_param.get("score", 5)  # Keep agent's score
        }
        corrected_data["parameters"].append(validated_param)
    
    # Check for missing datasources/fields/parameters (agent didn't include them)
    agent_ds_ids = {str(ds.get("id")) for ds in agent_datasources}
    db_ds_ids = set(db_datasource_map.keys())
    missing_ds = db_ds_ids - agent_ds_ids
    if missing_ds:
        validation_warnings.append(f"⚠️  Agent missed {len(missing_ds)} datasource(s): {missing_ds}")
    
    agent_field_ids = set()
    for ds in agent_datasources:
        agent_field_ids.update(str(f.get("id")) for f in ds.get("fields", []))
    db_field_ids = set(db_field_map.keys())
    missing_fields = db_field_ids - agent_field_ids
    if missing_fields:
        validation_warnings.append(f"⚠️  Agent missed {len(missing_fields)} field(s)")
    
    agent_param_ids = {str(p.get("id")) for p in agent_parameters}
    db_param_ids = set(db_parameter_map.keys())
    missing_params = db_param_ids - agent_param_ids
    if missing_params:
        validation_warnings.append(f"⚠️  Agent missed {len(missing_params)} parameter(s)")
    
    # Update field_data with corrected values
    is_valid = len(validation_errors) == 0
    
    validation_result = {
        "valid": is_valid,
        "errors": validation_errors,
        "warnings": validation_warnings,
        "corrected_data": corrected_data if validation_errors else None
    }
    
    if validation_errors:
        print(f"❌ Validation FAILED: {len(validation_errors)} error(s), {len(validation_warnings)} warning(s)")
        for err in validation_errors[:5]:  # Show first 5 errors
            print(f"   {err}")
    else:
        print(f"✅ Validation PASSED: {len(validation_warnings)} warning(s)")
        if validation_warnings:
            for warn in validation_warnings[:3]:  # Show first 3 warnings
                print(f"   {warn}")
    
    # Replace field_data with corrected data if there were errors
    if validation_errors and corrected_data:
        return {
            "field_validation": validation_result,
            "field_data": corrected_data  # Replace with validated data
        }
    
    return {"field_validation": validation_result}


def viz_agent_node(state: MigrationState):
    """LLM agent that scores visualization complexity by mark_class and includes fields."""
    print("🤖 Running Visualization Agent...")
    wb_id = state["workbook_id"]
    if not wb_id:
        return {"viz_data": {}}

    # Get worksheets
    worksheets = run_query(
        """
        SELECT id, workbook_id, name, datasource_id, columns_used, rows_used
        FROM worksheets
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

    # Get worksheet elements
    elements = run_query(
        """
        SELECT we.id,
               we.worksheet_id,
               we.pane_id,
               we.mark_class,
               we.element_type,
               we.encoding,
               we.style
        FROM worksheet_elements we
        JOIN worksheets w ON w.id = we.worksheet_id
        WHERE w.workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

    # Get all fields from datasources used by worksheets
    # This includes field complexity scores from field_agent analysis
    fields = run_query(
        """
        SELECT f.id,
               f.datasource_id,
               f.caption as name,
               f.internal_name,
               f.formula,
               f.data_type,
               f.role,
               f.is_calculated
        FROM fields f
        JOIN datasources d ON d.id = f.datasource_id
        JOIN worksheets w ON w.datasource_id = d.id
        WHERE w.workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

    # Get field analysis results from field_data to include scores
    field_data = state.get("field_data", {}) or {}
    field_scores_map = {}  # Map field_id -> {complexity_drivers, score}
    
    # Build a map of field scores from field_agent results
    for ds in field_data.get("datasources", []):
        for field in ds.get("fields", []):
            field_scores_map[field.get("id")] = {
                "complexity_drivers": field.get("complexity_drivers"),
                "score": field.get("score", 0)
            }
    
    # Enrich fields with scores from field_agent analysis
    enriched_fields = []
    for field in fields:
        field_id = field.get("id")
        field_info = field_scores_map.get(field_id, {"complexity_drivers": None, "score": 0})
        enriched_fields.append({
            **field,
            "complexity_drivers": field_info.get("complexity_drivers"),
            "score": field_info.get("score", 0)
        })

    payload = {
        "worksheets": worksheets,
        "worksheet_elements": elements,
        "fields": enriched_fields,
    }

    prompt = (
        VIZ_AGENT_PROMPT
        + "\n\nRAW_DATA_JSON:\n"
        + json.dumps(payload, indent=2)
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    data = extract_json(response.content)
    return {"viz_data": convert_uuids(data)}


def validate_viz_agent_node(state: MigrationState):
    """
    Validator agent that verifies viz_agent output against database.
    Checks worksheet IDs, mark_classes, and field references.
    """
    print("🔍 Validating Visualization Agent Output...")
    wb_id = state["workbook_id"]
    viz_data = state.get("viz_data", {}) or {}
    
    if not wb_id or not viz_data:
        return {"viz_validation": {"valid": False, "errors": ["Missing workbook_id or viz_data"]}}
    
    validation_errors = []
    validation_warnings = []
    corrected_data = {"worksheets": []}
    
    # Get actual data from database
    db_worksheets = run_query(
        """
        SELECT id, workbook_id, name, datasource_id, columns_used, rows_used
        FROM worksheets
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    db_elements = run_query(
        """
        SELECT we.id,
               we.worksheet_id,
               we.pane_id,
               we.mark_class,
               we.element_type,
               we.encoding,
               we.style
        FROM worksheet_elements we
        JOIN worksheets w ON w.id = we.worksheet_id
        WHERE w.workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    # Create lookup maps
    db_worksheet_map = {str(ws["id"]): ws for ws in db_worksheets}
    db_elements_by_worksheet = {}
    for elem in db_elements:
        ws_id = str(elem.get("worksheet_id"))
        if ws_id not in db_elements_by_worksheet:
            db_elements_by_worksheet[ws_id] = []
        db_elements_by_worksheet[ws_id].append(elem)
    
    # Validate worksheets
    agent_worksheets = viz_data.get("worksheets", [])
    for agent_ws in agent_worksheets:
        ws_id = str(agent_ws.get("id", ""))
        
        if ws_id not in db_worksheet_map:
            validation_errors.append(f"❌ HALLUCINATION: Worksheet ID {ws_id} does not exist in database")
            continue
        
        db_ws = db_worksheet_map[ws_id]
        
        # Verify name matches
        agent_name = agent_ws.get("name")
        db_name = db_ws.get("name")
        if agent_name != db_name:
            validation_warnings.append(
                f"⚠️  Worksheet {ws_id} name mismatch - Agent: '{agent_name}' vs DB: '{db_name}'"
            )
        
        # Verify datasource_id matches
        agent_ds_id = str(agent_ws.get("datasource_id", "")) if agent_ws.get("datasource_id") else None
        db_ds_id = str(db_ws.get("datasource_id", "")) if db_ws.get("datasource_id") else None
        if agent_ds_id != db_ds_id:
            validation_errors.append(
                f"❌ DATASOURCE MISMATCH: Worksheet {ws_id} - Agent: '{agent_ds_id}' vs DB: '{db_ds_id}'"
            )
            agent_ws["datasource_id"] = db_ds_id  # Use DB value
        
        # Validate mark_classes against actual elements
        db_elements_for_ws = db_elements_by_worksheet.get(ws_id, [])
        db_mark_classes = [str(elem.get("mark_class", "")).lower() for elem in db_elements_for_ws if elem.get("mark_class")]
        agent_mark_classes = [str(mc).lower() for mc in agent_ws.get("mark_classes", [])]
        
        # Check if agent's mark_classes match what's in DB
        for agent_mc in agent_mark_classes:
            if agent_mc not in db_mark_classes:
                validation_warnings.append(
                    f"⚠️  Worksheet {ws_id}: mark_class '{agent_mc}' not found in database elements"
                )
        
        # Validate field references
        agent_fields = agent_ws.get("fields", [])
        for agent_field in agent_fields:
            field_id = str(agent_field.get("id", ""))
            # Check if field exists in validated field_data
            field_data = state.get("field_data", {}) or {}
            field_exists = False
            for ds in field_data.get("datasources", []):
                for f in ds.get("fields", []):
                    if str(f.get("id")) == field_id:
                        field_exists = True
                        break
                if field_exists:
                    break
            
            if not field_exists:
                validation_warnings.append(
                    f"⚠️  Worksheet {ws_id}: Field {field_id} referenced but not found in field_data"
                )
        
        # Keep agent's analysis but use DB data for facts
        validated_ws = {
            "id": ws_id,
            "name": db_name,  # Use DB value
            "datasource_id": db_ds_id,  # Use DB value
            "viz_type": agent_ws.get("viz_type"),  # Keep agent's analysis
            "mark_classes": list(set(db_mark_classes)) if db_mark_classes else agent_ws.get("mark_classes", []),  # Use DB if available
            "dual_axis": agent_ws.get("dual_axis", False),  # Keep agent's analysis
            "viz_score": agent_ws.get("viz_score", 0),  # Keep agent's score
            "field_score": agent_ws.get("field_score", 0),  # Keep agent's score
            "complexity_score": agent_ws.get("complexity_score", 0),  # Keep agent's score
            "fields": agent_ws.get("fields", [])  # Keep agent's field list
        }
        corrected_data["worksheets"].append(validated_ws)
    
    # Check for missing worksheets
    agent_ws_ids = {str(ws.get("id")) for ws in agent_worksheets}
    db_ws_ids = set(db_worksheet_map.keys())
    missing_ws = db_ws_ids - agent_ws_ids
    if missing_ws:
        validation_warnings.append(f"⚠️  Agent missed {len(missing_ws)} worksheet(s): {missing_ws}")
    
    is_valid = len(validation_errors) == 0
    
    validation_result = {
        "valid": is_valid,
        "errors": validation_errors,
        "warnings": validation_warnings,
        "corrected_data": corrected_data if validation_errors else None
    }
    
    if validation_errors:
        print(f"❌ Validation FAILED: {len(validation_errors)} error(s), {len(validation_warnings)} warning(s)")
        for err in validation_errors[:5]:
            print(f"   {err}")
    else:
        print(f"✅ Validation PASSED: {len(validation_warnings)} warning(s)")
        if validation_warnings:
            for warn in validation_warnings[:3]:
                print(f"   {warn}")
    
    # Replace viz_data with corrected data if there were errors
    if validation_errors and corrected_data:
        return {
            "viz_validation": validation_result,
            "viz_data": corrected_data
        }
    
    return {"viz_validation": validation_result}


def layout_agent_node(state: MigrationState):
    """LLM agent that scores dashboard layout complexity."""
    print("🤖 Running Dashboard Layout Agent...")
    wb_id = state["workbook_id"]
    if not wb_id:
        return {"layout_data": {}}

    dashboards = run_query(
        """
        SELECT id, workbook_id, name, width, height, zones
        FROM dashboards
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

    # zones might be stored as text; we keep them as-is (string or json)
    payload = {
        "dashboards": dashboards,
    }

    prompt = (
        LAYOUT_AGENT_PROMPT
        + "\n\nRAW_DATA_JSON:\n"
        + json.dumps(payload, indent=2)
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    data = extract_json(response.content)
    return {"layout_data": convert_uuids(data)}


def validate_layout_agent_node(state: MigrationState):
    """
    Validator agent that verifies layout_agent output against database.
    Checks dashboard IDs, names, and zones structure.
    """
    print("🔍 Validating Layout Agent Output...")
    wb_id = state["workbook_id"]
    layout_data = state.get("layout_data", {}) or {}
    
    if not wb_id or not layout_data:
        return {"layout_validation": {"valid": False, "errors": ["Missing workbook_id or layout_data"]}}
    
    validation_errors = []
    validation_warnings = []
    corrected_data = {"dashboards": []}
    
    # Get actual data from database
    db_dashboards = run_query(
        """
        SELECT id, workbook_id, name, width, height, zones
        FROM dashboards
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )
    
    db_dashboard_map = {str(db["id"]): db for db in db_dashboards}
    
    # Validate dashboards
    agent_dashboards = layout_data.get("dashboards", [])
    for agent_db in agent_dashboards:
        db_id = str(agent_db.get("id", ""))
        
        if db_id not in db_dashboard_map:
            validation_errors.append(f"❌ HALLUCINATION: Dashboard ID {db_id} does not exist in database")
            continue
        
        db_dashboard = db_dashboard_map[db_id]
        
        # Verify name matches
        agent_name = agent_db.get("name")
        db_name = db_dashboard.get("name")
        if agent_name != db_name:
            validation_warnings.append(
                f"⚠️  Dashboard {db_id} name mismatch - Agent: '{agent_name}' vs DB: '{db_name}'"
            )
        
        # Verify dimensions match
        agent_width = agent_db.get("width")
        agent_height = agent_db.get("height")
        db_width = db_dashboard.get("width")
        db_height = db_dashboard.get("height")
        
        if agent_width != db_width or agent_height != db_height:
            validation_warnings.append(
                f"⚠️  Dashboard {db_id} dimensions mismatch - Agent: {agent_width}x{agent_height} vs DB: {db_width}x{db_height}"
            )
        
        # Keep agent's analysis but use DB data for facts
        validated_db = {
            "id": db_id,
            "name": db_name,  # Use DB value
            "width": db_width,  # Use DB value
            "height": db_height,  # Use DB value
            "is_floating": agent_db.get("is_floating", False),  # Keep agent's analysis
            "floating_count": agent_db.get("floating_count", 0),  # Keep agent's analysis
            "component_count": agent_db.get("component_count", 0),  # Keep agent's analysis
            "contained_sheet_ids": agent_db.get("contained_sheet_ids", []),  # Keep agent's analysis
            "layout_score": agent_db.get("layout_score", 0)  # Keep agent's score
        }
        corrected_data["dashboards"].append(validated_db)
    
    # Check for missing dashboards
    agent_db_ids = {str(db.get("id")) for db in agent_dashboards}
    db_db_ids = set(db_dashboard_map.keys())
    missing_dbs = db_db_ids - agent_db_ids
    if missing_dbs:
        validation_warnings.append(f"⚠️  Agent missed {len(missing_dbs)} dashboard(s): {missing_dbs}")
    
    is_valid = len(validation_errors) == 0
    
    validation_result = {
        "valid": is_valid,
        "errors": validation_errors,
        "warnings": validation_warnings,
        "corrected_data": corrected_data if validation_errors else None
    }
    
    if validation_errors:
        print(f"❌ Validation FAILED: {len(validation_errors)} error(s), {len(validation_warnings)} warning(s)")
        for err in validation_errors[:5]:
            print(f"   {err}")
    else:
        print(f"✅ Validation PASSED: {len(validation_warnings)} warning(s)")
        if validation_warnings:
            for warn in validation_warnings[:3]:
                print(f"   {warn}")
    
    # Replace layout_data with corrected data if there were errors
    if validation_errors and corrected_data:
        return {
            "layout_validation": validation_result,
            "layout_data": corrected_data
        }
    
    return {"layout_validation": validation_result}


def aggregator_node(state: MigrationState):
    """Aggregate field/viz/layout scores into final workbook report."""
    print("🔗 Aggregating Results...")

    field_data = state.get("field_data", {}) or {}
    viz_data = state.get("viz_data", {}) or {}
    layout_data = state.get("layout_data", {}) or {}

    datasources = field_data.get("datasources", []) or []
    parameters = field_data.get("parameters", []) or []
    worksheets = viz_data.get("worksheets", []) or []
    dashboards = layout_data.get("dashboards", []) or []

    # Calculate scores
    # Note: Since worksheets now include field scores, we need to be careful not to double-count
    
    # Option 1: Use worksheet complexity_score (which already includes viz + fields)
    # This is the recommended approach since worksheets now have combined scores
    total_worksheet_score = sum(ws.get("complexity_score", 0) for ws in worksheets)
    
    # Option 2: Separate calculation (for reporting purposes)
    total_viz_score = sum(ws.get("viz_score", ws.get("complexity_score", 0)) for ws in worksheets)
    total_worksheet_field_score = sum(ws.get("field_score", 0) for ws in worksheets)
    
    # Datasource-level field scores (for fields not used in worksheets, if any)
    # This captures fields that exist but aren't used in any worksheet
    total_datasource_field_score = sum(ds.get("complexity_score", 0) for ds in datasources)
    
    # Layout and parameter scores
    total_layout_score = sum(db.get("layout_score", 0) for db in dashboards)
    total_param_score = sum(p.get("score", 0) for p in parameters)

    # Total complexity score
    # Use worksheet complexity_score (which includes both viz and fields) + layout + params
    # We don't add datasource scores separately since they're already included in worksheet scores
    total_score = total_worksheet_score + total_layout_score + total_param_score

    migration_category = "Low"
    if total_score > 60:
        migration_category = "High"
    elif total_score > 20:
        migration_category = "Medium"

    # Include validation results in final report
    field_validation = state.get("field_validation", {})
    viz_validation = state.get("viz_validation", {})
    layout_validation = state.get("layout_validation", {})

    final_report = {
        "workbook": {
            "name": state["workbook_name"],
            "id": state["workbook_id"],
            "summary": {
                "total_complexity_score": total_score,
                "worksheet_score": total_worksheet_score,  # Combined viz + fields
                "worksheet_viz_score": total_viz_score,   # Visualization complexity only
                "worksheet_field_score": total_worksheet_field_score,  # Field complexity in worksheets
                "datasource_field_score": total_datasource_field_score,  # All field complexity
                "layout_score": total_layout_score,
                "parameter_score": total_param_score,
                "migration_category": migration_category,
            },
            "datasources": datasources,
            "parameters": parameters,
            "worksheets": worksheets,  # Now includes fields and combined scores
            "dashboards": dashboards,
            "validation": {
                "field_agent": {
                    "valid": field_validation.get("valid", True),
                    "error_count": len(field_validation.get("errors", [])),
                    "warning_count": len(field_validation.get("warnings", []))
                },
                "viz_agent": {
                    "valid": viz_validation.get("valid", True),
                    "error_count": len(viz_validation.get("errors", [])),
                    "warning_count": len(viz_validation.get("warnings", []))
                },
                "layout_agent": {
                    "valid": layout_validation.get("valid", True),
                    "error_count": len(layout_validation.get("errors", [])),
                    "warning_count": len(layout_validation.get("warnings", []))
                }
            }
        }
    }

    return {"final_report": convert_uuids(final_report)}


def html_agent_node(state: MigrationState):
    """LLM agent that generates HTML report from JSON."""
    print("🎨 Running HTML Generation Agent...")
    
    final_report = state.get("final_report", {})
    if not final_report:
        return {"html_report": "<html><body><h1>No data available</h1></body></html>"}
    
    # Prepare the prompt with the JSON report
    prompt = (
        HTML_AGENT_PROMPT
        + "\n\nJSON_REPORT_DATA:\n"
        + json.dumps(final_report, indent=2)
    )
    
    response = llm.invoke([HumanMessage(content=prompt)])
    html_content = extract_html(response.content)
    
    print("✅ HTML report generated")
    return {"html_report": html_content}


# ============================================================================
# 6. BUILD GRAPH
# ============================================================================

workflow = StateGraph(MigrationState)

workflow.add_node("setup", setup_node)
workflow.add_node("field_agent", field_agent_node)
workflow.add_node("validate_field", validate_field_agent_node)
workflow.add_node("viz_agent", viz_agent_node)
workflow.add_node("validate_viz", validate_viz_agent_node)
workflow.add_node("layout_agent", layout_agent_node)
workflow.add_node("validate_layout", validate_layout_agent_node)
workflow.add_node("aggregator", aggregator_node)
workflow.add_node("html_agent", html_agent_node)

workflow.set_entry_point("setup")
workflow.add_edge("setup", "field_agent")
workflow.add_edge("field_agent", "validate_field")
workflow.add_edge("validate_field", "viz_agent")
workflow.add_edge("viz_agent", "validate_viz")
workflow.add_edge("validate_viz", "layout_agent")
workflow.add_edge("layout_agent", "validate_layout")
workflow.add_edge("validate_layout", "aggregator")
workflow.add_edge("aggregator", "html_agent")
workflow.add_edge("html_agent", END)

app = workflow.compile()

# ============================================================================
# 7. EXECUTION (JSON + HTML)
# ============================================================================

def analyze_workbook_hierarchical(workbook_name: str):
    print(f"🚀 Starting Multi-Agent Analysis with Validators for: {workbook_name}")

    initial_state: MigrationState = {
        "workbook_name": workbook_name,
        "workbook_id": "",
        "field_data": {},
        "viz_data": {},
        "layout_data": {},
        "field_validation": {},
        "viz_validation": {},
        "layout_validation": {},
        "final_report": {},
        "html_report": "",
    }

    result = app.invoke(initial_state)
    report = result.get("final_report", {})
    html_report = result.get("html_report", "")
    
    report = convert_uuids(report)

    print("\n" + "=" * 60)
    print("📊 FINAL HIERARCHICAL REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2))

    # Save JSON with validated report naming
    safe_name = workbook_name.replace(" ", "_").replace("/", "_")
    json_filename = f"{safe_name}_validated_complexity_report1.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Save HTML with validated report naming
    html_filename = f"{safe_name}_validated_complexity_report1.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_report)

    print(f"\n💾 Saved VALIDATED JSON report to {json_filename}")
    print(f"💾 Saved VALIDATED HTML report to {html_filename}")
    print(f"   📋 Both reports include validation results against the database")
    
    # Print validation summary
    validation = report.get("workbook", {}).get("validation", {})
    print("\n" + "=" * 60)
    print("🔍 VALIDATION SUMMARY")
    print("=" * 60)
    for agent_name, val_result in validation.items():
        status = "✅ PASSED" if val_result.get("valid") else "❌ FAILED"
        print(f"{agent_name}: {status} ({val_result.get('error_count', 0)} errors, {val_result.get('warning_count', 0)} warnings)")


def list_available_workbooks():
    """Helper function to list all workbooks in the database."""
    try:
        query = "SELECT id, name FROM workbooks ORDER BY name LIMIT 20"
        result = run_query(query)
        print("\n" + "=" * 60)
        print("📚 AVAILABLE WORKBOOKS IN DATABASE")
        print("=" * 60)
        for row in result:
            print(f"  - {row.get('name')} (ID: {row.get('id')})")
        print("=" * 60 + "\n")
        return result
    except Exception as e:
        print(f"❌ Error listing workbooks: {e}")
        return None


if __name__ == "__main__":
    import sys
    
    # If --list flag, show available workbooks
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_available_workbooks()
        sys.exit(0)
    
    # Get workbook name from command line or use default
    workbook_name = sys.argv[1] if len(sys.argv) > 1 else "SalesSummary_BIGTEST_20x"
    
    print(f"\n💡 Tip: Use --list flag to see available workbooks")
    print(f"💡 Using workbook name: '{workbook_name}'\n")
    
    analyze_workbook_hierarchical(workbook_name)
