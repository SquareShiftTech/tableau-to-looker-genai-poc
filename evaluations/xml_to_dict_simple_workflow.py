"""
Simple 2-Agent Workflow for XML to Schema - POC
Following UML Pattern:
- Parsing Agent (combines Exploration + Parsing): XML → JSON → Schema → Relational
- Strategy Agent: Aggregate & recommend

Usage: python xml_to_dict_simple_workflow.py file1.xml file2.xml file3.xml
"""

import json
import sys
import os
from pathlib import Path
from typing import TypedDict, List, Dict, Any
from datetime import datetime

import xmltodict
from genson import SchemaBuilder
import psycopg2
from psycopg2.extras import Json

from langchain_google_vertexai import ChatVertexAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_FOLDER = Path("input_files/tableau")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "tableau_migration"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres")
}

DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "tableau-to-looker-migration")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")

# ============================================================================
# DATABASE SCHEMA (Simplified)
# ============================================================================

DATA_MODEL = """
CREATE TABLE IF NOT EXISTS raw_tableau_files (
    id SERIAL PRIMARY KEY,
    file_name TEXT,
    raw_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS json_schema (
    id INT PRIMARY KEY DEFAULT 1,
    schema_data JSONB NOT NULL,
    source_files TEXT[],
    updated_at TIMESTAMP DEFAULT NOW(),
    CHECK (id = 1)
);
"""

# ============================================================================
# STATE DEFINITION
# ============================================================================

class WorkflowState(TypedDict):
    """State for the workflow"""
    xml_files: List[str]
    json_data_list: List[Dict[str, Any]]
    schema: Dict[str, Any]
    table_counts: Dict[str, int]
    analysis: Dict[str, Any]
    status: str
    errors: List[str]


# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_db_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(**DB_CONFIG)


def initialize_database():
    """Initialize database schema"""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(DATA_MODEL)
        conn.commit()
    conn.close()
    return "Database initialized"


def store_json_and_schema(json_data_list: List[Dict], file_names: List[str]) -> Dict[str, Any]:
    """Store JSON data and generate schema"""
    conn = get_db_connection()
    file_ids = []
    
    # Store raw JSON
    for json_data, file_name in zip(json_data_list, file_names):
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO raw_tableau_files (file_name, raw_json) VALUES (%s, %s) RETURNING id",
                (file_name, Json(json_data))
            )
            file_ids.append(cur.fetchone()[0])
        conn.commit()
    
    # Generate and store unified schema
    builder = SchemaBuilder()
    for json_data in json_data_list:
        builder.add_object(json_data)
    schema = builder.to_schema()
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["title"] = "Tableau Workbook Schema"
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO json_schema (id, schema_data, source_files, updated_at)
            VALUES (1, %s, %s, NOW())
            ON CONFLICT (id) DO UPDATE SET schema_data = %s, source_files = %s, updated_at = NOW()
        """, (Json(schema), file_names, Json(schema), file_names))
        conn.commit()
    
    conn.close()
    return {"file_ids": file_ids, "schema": schema}


def get_table_counts() -> Dict[str, int]:
    """Get row counts from database"""
    conn = get_db_connection()
    counts = {}
    
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM raw_tableau_files")
        counts['raw_tableau_files'] = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM json_schema WHERE id = 1")
        counts['json_schema'] = cur.fetchone()[0]
    
    conn.close()
    return counts


# ============================================================================
# AGENT 1: PARSING AGENT (Exploration + Parsing combined)
# ============================================================================

def parsing_agent(state: WorkflowState) -> WorkflowState:
    """
    Parsing Agent - Combines Exploration + Parsing
    Step 1: Discover all components (XML → JSON)
    Step 2: Extract complete details (JSON → Schema → Relational storage)
    """
    print("\n🤖 Parsing Agent: Discovering components & extracting details...")
    
    llm = ChatVertexAI(
        model_name=LLM_MODEL,
        temperature=0.1,
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION
    )
    
    # Initialize database
    try:
        initialize_database()
        print("   ✅ Database initialized")
    except Exception as e:
        state['errors'].append(f"DB init: {str(e)}")
        print(f"   ⚠️  DB init warning: {str(e)}")
    
    # Step 1: Exploration - Convert XML to JSON (discover components)
    json_data_list = []
    file_names = []
    
    xml_files = state.get('xml_files', [])
    if not xml_files:
        # Auto-discover files
        xml_files = list(INPUT_FOLDER.glob("*.xml")) + list(INPUT_FOLDER.glob("*.twb"))
        xml_files = [str(f) for f in xml_files]
    
    for xml_path in xml_files:
        if not Path(xml_path).exists():
            print(f"   ⚠️  Skipping: {xml_path} (not found)")
            continue
        
        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                json_data = xmltodict.parse(f.read())
            json_data_list.append(json_data)
            file_names.append(Path(xml_path).name)
            print(f"   ✅ Discovered: {Path(xml_path).name}")
        except Exception as e:
            error_msg = f"Failed to convert {xml_path}: {str(e)}"
            state['errors'].append(error_msg)
            print(f"   ❌ {error_msg}")
    
    if not json_data_list:
        state['status'] = 'error'
        state['errors'].append("No valid XML files could be converted")
        return state
    
    # LLM validation of discovery
    try:
        response = llm.invoke(f"Validate discovery of {len(json_data_list)} Tableau XML file(s) converted to JSON. Confirm structure discovery.")
        print(f"   📋 Validation: {response.content[:150]}...")
    except Exception as e:
        print(f"   ⚠️  LLM validation skipped: {str(e)}")
    
    # Step 2: Parsing - Generate schema and store
    try:
        result = store_json_and_schema(json_data_list, file_names)
        state['schema'] = result['schema']
        state['json_data_list'] = json_data_list
        print(f"   ✅ Schema extracted: {len(result['schema'].get('properties', {}))} top-level properties")
        print(f"   ✅ Stored {len(result['file_ids'])} file(s) in database")
        
        # Get table counts
        counts = get_table_counts()
        state['table_counts'] = counts
        print(f"   ✅ Table counts: {counts}")
        
        state['status'] = 'parsed'
    except Exception as e:
        state['status'] = 'error'
        state['errors'].append(f"Parsing failed: {str(e)}")
        print(f"   ❌ Error: {e}")
    
    return state


# ============================================================================
# AGENT 2: STRATEGY AGENT
# ============================================================================

def strategy_agent(state: WorkflowState) -> WorkflowState:
    """
    Strategy Agent - Aggregate & recommend
    Analyzes parsed data and provides migration recommendations
    """
    print("\n🤖 Strategy Agent: Aggregating & recommending...")
    
    llm = ChatVertexAI(
        model_name=LLM_MODEL,
        temperature=0.1,
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION
    )
    
    # Use SQL Agent for data analysis
    try:
        db = SQLDatabase.from_uri(DATABASE_URL)
        sql_agent = create_sql_agent(
            llm=llm,
            db=db,
            verbose=False,
            handle_parsing_errors=True
        )
        
        # Strategic analysis questions
        analysis_questions = [
            "How many Tableau files have been processed?",
            "What is the structure of the JSON schema? How many top-level properties?",
            "Provide a summary of the Tableau workbook structure for migration planning."
        ]
        
        insights = []
        for question in analysis_questions:
            try:
                result = sql_agent.invoke({"input": question})
                insights.append({
                    "question": question,
                    "answer": result['output']
                })
                print(f"   📋 {question[:50]}...")
            except Exception as e:
                insights.append({
                    "question": question,
                    "error": str(e)
                })
        
    except Exception as e:
        print(f"   ⚠️  SQL Agent unavailable: {str(e)}")
        insights = [{"error": "SQL Agent not available"}]
    
    # Final LLM recommendations
    try:
        summary_prompt = f"""You are a migration strategy expert. Based on the following analysis:

- Files processed: {len(state.get('json_data_list', []))}
- Schema properties: {len(state.get('schema', {}).get('properties', {}))}
- Database records: {state.get('table_counts', {})}

Provide:
1. Complexity assessment
2. Key components identified (worksheets, dashboards, datasources)
3. Migration strategy recommendations
4. Potential challenges and solutions

Be concise and actionable."""
        
        response = llm.invoke(summary_prompt)
        recommendations = response.content
        print(f"   📋 Recommendations generated")
        
    except Exception as e:
        recommendations = f"Error generating recommendations: {str(e)}"
        print(f"   ⚠️  Recommendations error: {str(e)}")
    
    state['analysis'] = {
        "insights": insights,
        "recommendations": recommendations,
        "table_counts": state.get('table_counts', {}),
        "schema_properties_count": len(state.get('schema', {}).get('properties', {}))
    }
    state['status'] = 'completed'
    
    return state


# ============================================================================
# WORKFLOW CREATION
# ============================================================================

def create_workflow():
    """Create simple 2-agent workflow following UML pattern"""
    workflow = StateGraph(WorkflowState)
    
    workflow.add_node("parsing_agent", parsing_agent)
    workflow.add_node("strategy_agent", strategy_agent)
    
    workflow.set_entry_point("parsing_agent")
    workflow.add_edge("parsing_agent", "strategy_agent")
    workflow.add_edge("strategy_agent", END)
    
    return workflow.compile()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    print("=" * 60)
    print("🚀 Simple 2-Agent Workflow - XML to Schema (UML Pattern)")
    print("=" * 60)
    
    # Get XML files from command line
    if len(sys.argv) > 1:
        xml_files = sys.argv[1:]
    else:
        # Auto-discover files
        if INPUT_FOLDER.exists():
            xml_files = list(INPUT_FOLDER.glob("*.xml")) + list(INPUT_FOLDER.glob("*.twb"))
            xml_files = [str(f) for f in xml_files]
        else:
            xml_files = ["input_files/tableau/sales_summary_final.xml"]
    
    if not xml_files:
        print("❌ No XML files found")
        sys.exit(1)
    
    print(f"\n📄 Processing {len(xml_files)} file(s):")
    for f in xml_files:
        print(f"   - {f}")
    
    # Initialize state
    initial_state = {
        "xml_files": xml_files,
        "json_data_list": [],
        "schema": {},
        "table_counts": {},
        "analysis": {},
        "status": "started",
        "errors": []
    }
    
    # Run workflow
    print("\n" + "=" * 60)
    print("🔄 Starting Workflow...")
    print("=" * 60)
    
    workflow = create_workflow()
    result = workflow.invoke(initial_state)
    
    # Save outputs
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save JSON files
    for i, (xml_path, json_data) in enumerate(zip(xml_files, result.get('json_data_list', []))):
        json_file = output_dir / f"{Path(xml_path).stem}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved JSON: {json_file}")
    
    # Save schema
    if result.get('schema'):
        schema_file = output_dir / f"schema_{timestamp}.json"
        with open(schema_file, 'w', encoding='utf-8') as f:
            json.dump(result['schema'], f, indent=2, ensure_ascii=False)
        print(f"💾 Saved Schema: {schema_file}")
    
    # Save analysis
    if result.get('analysis'):
        analysis_file = output_dir / f"analysis_{timestamp}.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(result['analysis'], f, indent=2, ensure_ascii=False)
        print(f"💾 Saved Analysis: {analysis_file}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("✅ WORKFLOW COMPLETE")
    print("=" * 60)
    print(f"Status: {result['status']}")
    print(f"Files processed: {len(result.get('json_data_list', []))}")
    
    if result.get('schema'):
        print(f"Schema properties: {len(result['schema'].get('properties', {}))}")
    
    if result.get('table_counts'):
        print(f"Database records: {result['table_counts']}")
    
    if result.get('analysis', {}).get('recommendations'):
        print(f"\n📋 Recommendations:")
        print(result['analysis']['recommendations'][:500] + "...")
    
    if result.get('errors'):
        print(f"\n⚠️  Errors: {len(result['errors'])}")
        for error in result['errors']:
            print(f"   - {error}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
