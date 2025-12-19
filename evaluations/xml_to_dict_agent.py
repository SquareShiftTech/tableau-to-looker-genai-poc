"""
Tableau Migration Agent Application
- Ingestion Agent: Parses and loads Tableau XML
- Query Agent: Natural language queries on data model
"""

import json
from pathlib import Path
from typing import TypedDict, Annotated
import operator

import xmltodict
from genson import SchemaBuilder
import psycopg2
from psycopg2.extras import Json

from langchain_google_vertexai import ChatVertexAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode


# ============================================================================
# CONFIG
# ============================================================================

INPUT_FOLDER = Path("input_files/tableau")

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "tableau_migration",
    "user": "postgres",
    "password": "postgres"
}

DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# ============================================================================
# DATA MODEL DDL
# ============================================================================

DATA_MODEL = """
CREATE TABLE IF NOT EXISTS json_schema (
    id INT PRIMARY KEY DEFAULT 1,
    schema_data JSONB NOT NULL,
    source_files TEXT[],
    updated_at TIMESTAMP DEFAULT NOW(),
    CHECK (id = 1)
);

CREATE TABLE IF NOT EXISTS raw_tableau_files (
    id SERIAL PRIMARY KEY,
    file_name TEXT,
    raw_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_file_id INT REFERENCES raw_tableau_files(id),
    name TEXT,
    version TEXT,
    site TEXT,
    project_path TEXT,
    manifest JSONB
);

CREATE TABLE IF NOT EXISTS datasources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    caption TEXT,
    connection_type TEXT,
    db_name TEXT,
    db_schema TEXT,
    is_extract BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    datasource_id UUID REFERENCES datasources(id) ON DELETE CASCADE,
    caption TEXT,
    internal_name TEXT,
    formula TEXT,
    data_type TEXT,
    role TEXT,
    is_calculated BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    data_type TEXT,
    current_value TEXT,
    range_options JSONB
);

CREATE TABLE IF NOT EXISTS worksheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    datasource_id UUID REFERENCES datasources(id),
    columns_used TEXT[],
    rows_used TEXT[]
);

CREATE TABLE IF NOT EXISTS worksheet_elements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worksheet_id UUID REFERENCES worksheets(id) ON DELETE CASCADE,
    pane_id TEXT,
    mark_class TEXT,
    element_type TEXT,
    encoding JSONB,
    style JSONB
);

CREATE TABLE IF NOT EXISTS dashboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    width INTEGER,
    height INTEGER,
    zones JSONB
);

CREATE TABLE IF NOT EXISTS dashboard_components (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID REFERENCES dashboards(id) ON DELETE CASCADE,
    worksheet_id UUID REFERENCES worksheets(id),
    component_type TEXT,
    x_pos INTEGER,
    y_pos INTEGER,
    width INTEGER,
    height INTEGER,
    is_visible BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workbook_id UUID REFERENCES workbooks(id) ON DELETE CASCADE,
    name TEXT,
    action_type TEXT,
    source_object_name TEXT,
    target_object_name TEXT,
    logic_details JSONB
);
"""

# ============================================================================
# INGESTION SQL QUERIES
# ============================================================================

INGESTION_QUERIES = {
    "workbooks": """
        INSERT INTO workbooks (raw_file_id, name, version, site, project_path, manifest)
        SELECT r.id, COALESCE(r.raw_json->'workbook'->'repository-location'->>'@id', r.file_name),
            r.raw_json->'workbook'->>'@version', r.raw_json->'workbook'->'repository-location'->>'@site',
            r.raw_json->'workbook'->'repository-location'->>'@path', r.raw_json->'workbook'->'document-format-change-manifest'
        FROM raw_tableau_files r WHERE NOT EXISTS (SELECT 1 FROM workbooks w WHERE w.raw_file_id = r.id);
    """,
    "datasources": """
        INSERT INTO datasources (workbook_id, name, caption, connection_type, db_name, db_schema)
        SELECT DISTINCT w.id, ds->>'@name', ds->>'@caption', ds->'connection'->>'@class',
            ds->'connection'->'named-connections'->'named-connection'->'connection'->>'@CATALOG',
            ds->'connection'->'named-connections'->'named-connection'->'connection'->>'@schema'
        FROM raw_tableau_files r JOIN workbooks w ON w.raw_file_id = r.id
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(r.raw_json->'workbook'->'datasources'->'datasource') = 'array' 
            THEN r.raw_json->'workbook'->'datasources'->'datasource'
            WHEN r.raw_json->'workbook'->'datasources'->'datasource' IS NOT NULL
            THEN jsonb_build_array(r.raw_json->'workbook'->'datasources'->'datasource') ELSE '[]'::jsonb END
        ) AS ds WHERE r.raw_json->'workbook'->'datasources'->'datasource' IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM datasources d2 WHERE d2.workbook_id = w.id AND d2.name = ds->>'@name');
    """,
    "fields": """
        INSERT INTO fields (datasource_id, caption, internal_name, formula, data_type, role, is_calculated)
        SELECT DISTINCT d.id, col->>'@caption', col->>'@name', col->'calculation'->>'@formula',
            col->>'@datatype', col->>'@role', (col->'calculation' IS NOT NULL)
        FROM raw_tableau_files r JOIN workbooks w ON w.raw_file_id = r.id
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(r.raw_json->'workbook'->'datasources'->'datasource') = 'array' 
            THEN r.raw_json->'workbook'->'datasources'->'datasource'
            WHEN r.raw_json->'workbook'->'datasources'->'datasource' IS NOT NULL
            THEN jsonb_build_array(r.raw_json->'workbook'->'datasources'->'datasource') ELSE '[]'::jsonb END
        ) AS ds JOIN datasources d ON d.workbook_id = w.id AND d.name = ds->>'@name'
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(ds->'column') = 'array' THEN ds->'column'
            WHEN ds->'column' IS NOT NULL THEN jsonb_build_array(ds->'column') ELSE '[]'::jsonb END
        ) AS col WHERE ds->'column' IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM fields f2 WHERE f2.datasource_id = d.id AND f2.internal_name = col->>'@name');
    """,
    "worksheets": """
        INSERT INTO worksheets (workbook_id, name, datasource_id, columns_used, rows_used)
        SELECT DISTINCT w.id, ws->>'@name', d.id,
            CASE WHEN ws->'table'->>'cols' IS NOT NULL AND ws->'table'->>'cols' != ''
            THEN string_to_array(regexp_replace(ws->'table'->>'cols', '[\\[\\]]', '', 'g'), '][') ELSE NULL END,
            CASE WHEN ws->'table'->>'rows' IS NOT NULL AND ws->'table'->>'rows' != ''
            THEN string_to_array(regexp_replace(ws->'table'->>'rows', '[\\[\\]]', '', 'g'), '][') ELSE NULL END
        FROM raw_tableau_files r JOIN workbooks w ON w.raw_file_id = r.id
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(r.raw_json->'workbook'->'worksheets'->'worksheet') = 'array' 
            THEN r.raw_json->'workbook'->'worksheets'->'worksheet'
            WHEN r.raw_json->'workbook'->'worksheets'->'worksheet' IS NOT NULL
            THEN jsonb_build_array(r.raw_json->'workbook'->'worksheets'->'worksheet') ELSE '[]'::jsonb END
        ) AS ws LEFT JOIN datasources d ON d.workbook_id = w.id AND d.name = ws->'table'->'view'->'datasources'->'datasource'->>'@name'
        WHERE r.raw_json->'workbook'->'worksheets'->'worksheet' IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM worksheets ws2 WHERE ws2.workbook_id = w.id AND ws2.name = ws->>'@name');
    """,
    "worksheet_elements": """
        INSERT INTO worksheet_elements (worksheet_id, pane_id, mark_class, element_type, encoding, style)
        SELECT DISTINCT wks.id, pane->>'@id', pane->'mark'->>'@class', 'pane', pane->'encodings', pane->'style'
        FROM raw_tableau_files r JOIN workbooks w ON w.raw_file_id = r.id
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(r.raw_json->'workbook'->'worksheets'->'worksheet') = 'array' 
            THEN r.raw_json->'workbook'->'worksheets'->'worksheet'
            WHEN r.raw_json->'workbook'->'worksheets'->'worksheet' IS NOT NULL
            THEN jsonb_build_array(r.raw_json->'workbook'->'worksheets'->'worksheet') ELSE '[]'::jsonb END
        ) AS ws JOIN worksheets wks ON wks.workbook_id = w.id AND wks.name = ws->>'@name'
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(ws->'table'->'panes'->'pane') = 'array' THEN ws->'table'->'panes'->'pane'
            WHEN ws->'table'->'panes'->'pane' IS NOT NULL THEN jsonb_build_array(ws->'table'->'panes'->'pane') ELSE '[]'::jsonb END
        ) AS pane WHERE ws->'table'->'panes'->'pane' IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM worksheet_elements we2 WHERE we2.worksheet_id = wks.id AND we2.pane_id = pane->>'@id');
    """,
    "dashboards": """
        INSERT INTO dashboards (workbook_id, name, width, height, zones)
        SELECT DISTINCT w.id, db->>'@name', (db->'size'->>'@maxwidth')::INTEGER, (db->'size'->>'@maxheight')::INTEGER, db->'zones'
        FROM raw_tableau_files r JOIN workbooks w ON w.raw_file_id = r.id
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(r.raw_json->'workbook'->'dashboards'->'dashboard') = 'array' 
            THEN r.raw_json->'workbook'->'dashboards'->'dashboard'
            WHEN r.raw_json->'workbook'->'dashboards'->'dashboard' IS NOT NULL
            THEN jsonb_build_array(r.raw_json->'workbook'->'dashboards'->'dashboard') ELSE '[]'::jsonb END
        ) AS db WHERE r.raw_json->'workbook'->'dashboards'->'dashboard' IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM dashboards d2 WHERE d2.workbook_id = w.id AND d2.name = db->>'@name');
    """,
    "dashboard_components": """
        WITH RECURSIVE zone_tree AS (
            SELECT d.id as dashboard_id, z->>'@id' as zone_id, z->>'@type-v2' as component_type,
                (z->>'@x')::INTEGER as x_pos, (z->>'@y')::INTEGER as y_pos,
                (z->>'@w')::INTEGER as width, (z->>'@h')::INTEGER as height, z->>'@param' as param, z->'zone' as child_zones
            FROM dashboards d
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE WHEN jsonb_typeof(d.zones->'zone') = 'array' THEN d.zones->'zone'
                WHEN d.zones->'zone' IS NOT NULL THEN jsonb_build_array(d.zones->'zone') ELSE '[]'::jsonb END
            ) AS z WHERE d.zones->'zone' IS NOT NULL
            UNION ALL
            SELECT zt.dashboard_id, cz->>'@id', cz->>'@type-v2', (cz->>'@x')::INTEGER, (cz->>'@y')::INTEGER,
                (cz->>'@w')::INTEGER, (cz->>'@h')::INTEGER, cz->>'@param', cz->'zone'
            FROM zone_tree zt
            CROSS JOIN LATERAL jsonb_array_elements(
                CASE WHEN jsonb_typeof(zt.child_zones) = 'array' THEN zt.child_zones
                WHEN zt.child_zones IS NOT NULL AND jsonb_typeof(zt.child_zones) = 'object' THEN jsonb_build_array(zt.child_zones) ELSE '[]'::jsonb END
            ) AS cz WHERE zt.child_zones IS NOT NULL
        )
        INSERT INTO dashboard_components (dashboard_id, worksheet_id, component_type, x_pos, y_pos, width, height, is_visible)
        SELECT DISTINCT zt.dashboard_id, ws.id, zt.component_type, zt.x_pos, zt.y_pos, zt.width, zt.height, TRUE
        FROM zone_tree zt LEFT JOIN worksheets ws ON ws.name = zt.param
        WHERE zt.zone_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM dashboard_components dc2 WHERE dc2.dashboard_id = zt.dashboard_id 
            AND COALESCE(dc2.x_pos, 0) = COALESCE(zt.x_pos, 0) AND COALESCE(dc2.y_pos, 0) = COALESCE(zt.y_pos, 0));
    """,
    "actions": """
        INSERT INTO actions (workbook_id, name, action_type, source_object_name, logic_details)
        SELECT DISTINCT w.id, act->>'@name', act->'activation'->>'@type', act->'source'->>'@worksheet', act
        FROM raw_tableau_files r JOIN workbooks w ON w.raw_file_id = r.id
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_typeof(r.raw_json->'workbook'->'actions'->'action') = 'array' 
            THEN r.raw_json->'workbook'->'actions'->'action'
            WHEN r.raw_json->'workbook'->'actions'->'action' IS NOT NULL
            THEN jsonb_build_array(r.raw_json->'workbook'->'actions'->'action') ELSE '[]'::jsonb END
        ) AS act WHERE r.raw_json->'workbook'->'actions'->'action' IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM actions a2 WHERE a2.workbook_id = w.id AND a2.name = act->>'@name');
    """
}


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


# ============================================================================
# INGESTION TOOLS
# ============================================================================

@tool
def initialize_database() -> str:
    """Initialize database schema. Creates all required tables."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(DATA_MODEL)
        conn.commit()
    conn.close()
    return "Database initialized successfully"


@tool
def list_xml_files() -> str:
    """List all XML/TWB files in the input folder."""
    files = list(INPUT_FOLDER.glob("*.xml")) + list(INPUT_FOLDER.glob("*.twb"))
    if not files:
        return f"No XML/TWB files found in {INPUT_FOLDER}"
    return f"Found {len(files)} files: {[f.name for f in files]}"


@tool
def convert_and_store_files() -> str:
    """Convert all XML files to JSON and store in PostgreSQL."""
    files = list(INPUT_FOLDER.glob("*.xml")) + list(INPUT_FOLDER.glob("*.twb"))
    if not files:
        return "No files to process"
    
    conn = get_db_connection()
    file_ids = []
    json_data_list = []
    file_names = []
    
    for xml_path in files:
        # Convert XML to JSON
        with open(xml_path, 'r', encoding='utf-8') as f:
            json_data = xmltodict.parse(f.read())
        
        json_data_list.append(json_data)
        file_names.append(xml_path.name)
        
        # Store in DB
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO raw_tableau_files (file_name, raw_json) VALUES (%s, %s) RETURNING id",
                (xml_path.name, Json(json_data))
            )
            file_ids.append(cur.fetchone()[0])
        conn.commit()
    
    # Generate and store unified schema
    builder = SchemaBuilder()
    for json_data in json_data_list:
        builder.add_object(json_data)
    schema = builder.to_schema()
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO json_schema (id, schema_data, source_files, updated_at)
            VALUES (1, %s, %s, NOW())
            ON CONFLICT (id) DO UPDATE SET schema_data = %s, source_files = %s, updated_at = NOW()
        """, (Json(schema), file_names, Json(schema), file_names))
        conn.commit()
    
    conn.close()
    return f"Converted and stored {len(files)} files. File IDs: {file_ids}"


@tool
def ingest_to_tables() -> str:
    """Ingest data from raw JSON into relational tables."""
    conn = get_db_connection()
    results = []
    
    order = ["workbooks", "datasources", "fields", "worksheets", "worksheet_elements", 
             "dashboards", "dashboard_components", "actions"]
    
    for table in order:
        try:
            with conn.cursor() as cur:
                cur.execute(INGESTION_QUERIES[table])
                rows = cur.rowcount
                conn.commit()
            results.append(f"{table}: {rows} rows")
        except Exception as e:
            conn.rollback()
            results.append(f"{table}: ERROR - {str(e)[:50]}")
    
    conn.close()
    return "Ingestion complete. " + ", ".join(results)


@tool
def get_table_counts() -> str:
    """Get row counts for all tables."""
    conn = get_db_connection()
    tables = ["workbooks", "datasources", "fields", "worksheets", "worksheet_elements", 
              "dashboards", "dashboard_components", "actions"]
    counts = {}
    
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
    
    conn.close()
    return f"Table counts: {json.dumps(counts, indent=2)}"


@tool
def truncate_all_tables() -> str:
    """Truncate all tables for fresh start."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            TRUNCATE TABLE actions, dashboard_components, dashboards, 
            worksheet_elements, worksheets, fields, parameters, datasources, 
            workbooks, raw_tableau_files, json_schema CASCADE;
        """)
        conn.commit()
    conn.close()
    return "All tables truncated"


# ============================================================================
# AGENT STATE
# ============================================================================

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    next_action: str


# ============================================================================
# INGESTION AGENT
# ============================================================================

def create_ingestion_agent():
    """Create LangGraph agent for ingestion."""
    
    llm = ChatVertexAI(model="gemini-2.0-flash-001", temperature=0)
    
    tools = [
        initialize_database,
        list_xml_files,
        convert_and_store_files,
        ingest_to_tables,
        get_table_counts,
        truncate_all_tables
    ]
    
    llm_with_tools = llm.bind_tools(tools)
    
    def agent_node(state: AgentState):
        """Agent decides what to do next."""
        system = SystemMessage(content="""You are a Tableau ingestion agent. Your job is to:
1. Initialize the database (if needed)
2. List and convert XML files to JSON
3. Store raw JSON in PostgreSQL
4. Ingest data into relational tables
5. Report final counts

Available tools:
- initialize_database: Create tables
- list_xml_files: See what files are available
- convert_and_store_files: Convert XML to JSON and store
- ingest_to_tables: Populate relational tables from raw JSON
- get_table_counts: Show how many rows in each table
- truncate_all_tables: Clear all data (use with --fresh)

Execute the full ingestion pipeline step by step.""")
        
        response = llm_with_tools.invoke([system] + state["messages"])
        return {"messages": [response]}
    
    def should_continue(state: AgentState):
        """Check if agent should continue or end."""
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return "end"
    
    # Build graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()


# ============================================================================
# QUERY AGENT (SQL Agent for natural language queries)
# ============================================================================

def create_query_agent():
    """Create SQL Agent for natural language queries on the data model."""
    
    llm = ChatVertexAI(model="gemini-2.0-flash-001", temperature=0)
    db = SQLDatabase.from_uri(DATABASE_URL)
    
    agent = create_sql_agent(
        llm=llm,
        db=db,
        verbose=True,
        handle_parsing_errors=True,
        prefix="""You are a Tableau migration assessment agent. You help users query the Tableau metadata stored in PostgreSQL.

Available tables:
- workbooks: Tableau workbook files (name, version, site)
- datasources: Data connections (connection_type, db_name)
- fields: Columns and calculations (formula, data_type, is_calculated)
- worksheets: Individual charts (columns_used, rows_used)
- worksheet_elements: Panes and marks in worksheets
- dashboards: Dashboard layouts (width, height)
- dashboard_components: What's inside dashboards
- actions: Filter/URL actions

Help users understand their Tableau environment for migration planning."""
    )
    
    return agent


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--fresh', action='store_true', help='Truncate all tables before ingestion')
    parser.add_argument('--query', action='store_true', help='Start query mode')
    args = parser.parse_args()
    query = True
    
    if args.query or query:
        # Query mode
        print("=" * 60)
        print("🔍 Tableau Query Agent")
        print("=" * 60)
        print("Ask questions about your Tableau workbooks. Type 'exit' to quit.\n")
        
        agent = create_query_agent()
        
        while True:
            question = input("You: ").strip()
            if question.lower() == 'exit':
                break
            if question:
                result = agent.invoke({"input": question})
                print(f"\nAgent: {result['output']}\n")
    
    else:
        # Ingestion mode
        print("=" * 60)
        print("📁 Tableau Ingestion Agent")
        print("=" * 60)
        
        agent = create_ingestion_agent()
        
        if args.fresh:
            initial_message = "Start fresh ingestion: truncate all tables, then initialize database, convert files, ingest to tables, and show final counts."
        else:
            initial_message = "Run ingestion: initialize database if needed, convert any new files, ingest to tables, and show final counts."
        
        result = agent.invoke({
            "messages": [HumanMessage(content=initial_message)]
        })
        
        # Print conversation
        print("\n📋 Agent Execution Log:")
        for msg in result["messages"]:
            if hasattr(msg, 'content') and msg.content:
                role = msg.__class__.__name__.replace("Message", "")
                print(f"\n[{role}]: {msg.content[:500]}")
        
        print("\n" + "=" * 60)
        print("✅ Ingestion complete!")
        print("=" * 60)


if __name__ == "__main__":
    main()