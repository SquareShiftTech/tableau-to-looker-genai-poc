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
You are a highly strict **Tableau Field Logic Analyzer**.  
You MUST output JSON only. No explanations before or after. No markdown.

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
2. Determine EXACTLY ONE primary issue type from this set:
   - "LOD"
   - "Table Calculation"
   - "Date Function"
   - "Aggregation"
   - "Arithmetic / Logic"
   - "Simple"
   - "None"

3. Assign EXACT score based on these **strict, numeric rules**:

| Issue Type           | Score |
|----------------------|--------|
| LOD                  | 10     |
| Table Calculation    | 5      |
| Date Function        | 2      |
| Aggregation          | 1      |
| Arithmetic / Logic   | 1      |
| Simple               | 0      |
| None (no formula)    | 0      |

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
          "issue": "LOD | Table Calculation | Date Function | Aggregation | Arithmetic / Logic | Simple | None",
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
You are a strict **Tableau Visualization Analyzer**.  
Output JSON only. No markdown. No explanation.

---------------------------------------------------------------------
### INPUT
{
  "worksheets": [...],
  "worksheet_elements": [...]
}

Each worksheet_element has:
- worksheet_id
- mark_class (string)
- pane_id
- element_type
- encoding
- style

---------------------------------------------------------------------
### SCORING RULES

Base score by viz type:

| Viz Type   | Score |
|------------|--------|
| bar        | 1 |
| line       | 1 |
| area       | 1 |
| pie        | 1 |
| text       | 1 |
| scatter    | 1 |
| map        | 3 |
| polygon    | 8 |
| heatmap    | 10 |
| gantt      | 10 |
| path       | 10 |
| none       | 0 |

PRIMARY viz type = the mark_class with HIGHEST score.

Dual-axis = true IF:
- Any mark_class in {bar, line, area} appears MORE THAN ONCE inside same worksheet.

FINAL complexity_score =
- base_chart_score + 3 IF dual-axis = true

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
      "complexity_score": number
    }
  ]
}
</JSON>

Rules:
- Never omit keys.
- mark_classes must be a deduped list.
- viz_type must be lowercase.
- If no elements exist → viz_type="none", dual_axis=false, score=0.
"""

LAYOUT_AGENT_PROMPT = """
You are a strict **Tableau Dashboard Layout Analyzer**.  
Output JSON ONLY between <JSON> and </JSON>.

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
### SCORING RULES

Start with:
layout_score = 0 if zones = null or empty  
layout_score = 1 if zones exist AND count ≥ 1

Then:
- If ANY zone has floating=true → add +8  
- If number_of_zones > 15 → add +5  

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
You are a **Professional HTML Report Generator** for Tableau Migration Assessment.

Your task is to convert a JSON complexity analysis report into a beautiful, professional HTML report.

---------------------------------------------------------------------
### INPUT JSON STRUCTURE

{
  "workbook": {
    "name": "string",
    "id": "string",
    "summary": {
      "total_complexity_score": number,
      "field_score": number,
      "viz_score": number,
      "layout_score": number,
      "parameter_score": number,
      "migration_category": "Low | Medium | High"
    },
    "datasources": [...],
    "parameters": [...],
    "worksheets": [...],
    "dashboards": [...]
  }
}

---------------------------------------------------------------------
### HTML REQUIREMENTS

1. **Modern, Professional Design**:
   - Use modern CSS with a clean, professional color scheme
   - Include proper typography (fonts, sizes, spacing)
   - Use a responsive layout
   - Add subtle shadows, borders, and hover effects

2. **Color Coding**:
   - Low complexity: Green (#28a745)
   - Medium complexity: Orange (#ffc107)
   - High complexity: Red (#dc3545)
   - Use these colors for badges, highlights, and visual indicators

3. **Structure**:
   - Header with workbook name and report title
   - Executive Summary section with key metrics in cards/boxes
   - Detailed sections for: Datasources, Parameters, Worksheets, Dashboards
   - Each section should have tables with proper styling
   - Footer with generation timestamp

4. **Visual Elements**:
   - Use badges/pills for complexity scores and categories
   - Tables with alternating row colors
   - Icons or visual indicators where appropriate
   - Progress bars or visual representations for scores

5. **Data Presentation**:
   - Format numbers properly
   - Show formulas in code-style blocks
   - Make tables sortable or at least well-formatted
   - Group related information logically

---------------------------------------------------------------------
### OUTPUT REQUIREMENTS

- Return ONLY the complete HTML document
- Include embedded CSS in <style> tag
- Include all HTML structure (DOCTYPE, html, head, body)
- NO markdown code blocks, NO explanations
- Just the raw HTML string

---------------------------------------------------------------------
### EXAMPLE STRUCTURE

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tableau Migration Assessment Report</title>
    <style>
        /* Modern CSS styles */
    </style>
</head>
<body>
    <div class="container">
        <header>...</header>
        <section class="summary">...</section>
        <section class="datasources">...</section>
        <section class="worksheets">...</section>
        <section class="dashboards">...</section>
        <footer>...</footer>
    </div>
</body>
</html>

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

    # Final Output
    final_report: Dict[str, Any]
    html_report: str  # New field for HTML output


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


def viz_agent_node(state: MigrationState):
    """LLM agent that scores visualization complexity by mark_class."""
    print("🤖 Running Visualization Agent...")
    wb_id = state["workbook_id"]
    if not wb_id:
        return {"viz_data": {}}

    worksheets = run_query(
        """
        SELECT id, workbook_id, name, datasource_id, columns_used, rows_used
        FROM worksheets
        WHERE workbook_id = :wb;
        """,
        {"wb": wb_id},
    )

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

    payload = {
        "worksheets": worksheets,
        "worksheet_elements": elements,
    }

    prompt = (
        VIZ_AGENT_PROMPT
        + "\n\nRAW_DATA_JSON:\n"
        + json.dumps(payload, indent=2)
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    data = extract_json(response.content)
    return {"viz_data": convert_uuids(data)}


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

    # Total scores based on LLM scoring
    total_field_score = sum(ds.get("complexity_score", 0) for ds in datasources)
    total_viz_score = sum(ws.get("complexity_score", 0) for ws in worksheets)
    total_layout_score = sum(db.get("layout_score", 0) for db in dashboards)
    total_param_score = sum(p.get("score", 0) for p in parameters)

    total_score = total_field_score + total_viz_score + total_layout_score + total_param_score

    migration_category = "Low"
    if total_score > 60:
        migration_category = "High"
    elif total_score > 20:
        migration_category = "Medium"

    final_report = {
        "workbook": {
            "name": state["workbook_name"],
            "id": state["workbook_id"],
            "summary": {
                "total_complexity_score": total_score,
                "field_score": total_field_score,
                "viz_score": total_viz_score,
                "layout_score": total_layout_score,
                "parameter_score": total_param_score,
                "migration_category": migration_category,
            },
            "datasources": datasources,
            "parameters": parameters,
            "worksheets": worksheets,
            "dashboards": dashboards,
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
workflow.add_node("viz_agent", viz_agent_node)
workflow.add_node("layout_agent", layout_agent_node)
workflow.add_node("aggregator", aggregator_node)
workflow.add_node("html_agent", html_agent_node)  # New HTML agent node

workflow.set_entry_point("setup")
workflow.add_edge("setup", "field_agent")
workflow.add_edge("field_agent", "viz_agent")
workflow.add_edge("viz_agent", "layout_agent")
workflow.add_edge("layout_agent", "aggregator")
workflow.add_edge("aggregator", "html_agent")  # HTML agent runs after aggregator
workflow.add_edge("html_agent", END)

app = workflow.compile()

# ============================================================================
# 7. EXECUTION (JSON + HTML)
# ============================================================================

def analyze_workbook_hierarchical(workbook_name: str):
    print(f"🚀 Starting Multi-Agent Analysis for: {workbook_name}")

    initial_state: MigrationState = {
        "workbook_name": workbook_name,
        "workbook_id": "",
        "field_data": {},
        "viz_data": {},
        "layout_data": {},
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

    # Save JSON
    safe_name = workbook_name.replace(" ", "_").replace("/", "_")
    json_filename = f"{safe_name}_full_analysis.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Save HTML
    html_filename = f"{safe_name}_full_analysis.html"
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_report)

    print(f"\n💾 Saved JSON to {json_filename}")
    print(f"💾 Saved HTML to {html_filename}")


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

