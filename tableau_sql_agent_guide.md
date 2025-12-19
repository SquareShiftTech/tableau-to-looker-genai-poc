# Tableau Migration Accelerator - SQL Agent Implementation

Complete implementation guide for transforming Tableau XML to PostgreSQL using LangGraph with SQL Agent and Vertex AI Gemini.

---

## Project Structure

```
tableau-sql-agent/
├── pyproject.toml
├── .env
├── .env.example
├── README.md
├── config.py
├── database/
│   ├── __init__.py
│   └── db_manager.py
├── tools/
│   ├── __init__.py
│   └── json_analyzer.py
├── agents/
│   ├── __init__.py
│   ├── workflow.py
│   └── prompts.py
├── main.py
└── test_data/
    └── sample_tableau.xml
```

---

## 1. pyproject.toml

```toml
[project]
name = "tableau-sql-agent"
version = "0.1.0"
description = "Tableau to PostgreSQL migration accelerator using LangGraph and SQL Agent"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
readme = "README.md"
requires-python = ">=3.10"

dependencies = [
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-google-vertexai>=2.0.0",
    "langchain-community>=0.3.0",
    "google-cloud-aiplatform>=1.70.0",
    "psycopg2-binary>=2.9.9",
    "sqlalchemy>=2.0.23",
    "xmltodict>=0.13.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["setuptools>=68.0.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
target-version = "py310"
```

---

## 2. .env.example

```env
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1

# PostgreSQL Configuration
DB_HOST=localhost
DB_NAME=tableau_migration
DB_USER=postgres
DB_PASSWORD=your_password
DB_PORT=5432

# Agent Configuration
LLM_MODEL=gemini-2.0-flash-exp
LLM_TEMPERATURE=0.1
```

---

## 3. config.py

```python
"""Configuration settings for the application"""
import os
from dotenv import load_dotenv

load_dotenv()

# Google Cloud Config
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Database Config
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "tableau_migration"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))
}

# LLM Config
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.1))
```

---

## 4. database/__init__.py

```python
"""Database package initialization"""
from .db_manager import DatabaseManager

__all__ = ["DatabaseManager"]
```

---

## 5. database/db_manager.py

```python
"""PostgreSQL database manager for raw JSON storage"""
import psycopg2
from psycopg2.extras import Json
from typing import Dict, Any, List, Optional
from config import DB_CONFIG


class DatabaseManager:
    """Handles all PostgreSQL database operations"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def get_connection(self):
        """Create database connection"""
        return psycopg2.connect(**self.config)
    
    def initialize_database(self):
        """Create raw storage table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_tableau_files (
                id SERIAL PRIMARY KEY,
                file_name VARCHAR(255) UNIQUE NOT NULL,
                raw_json JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                file_hash VARCHAR(64)
            );
            
            CREATE INDEX IF NOT EXISTS idx_file_name ON raw_tableau_files(file_name);
            CREATE INDEX IF NOT EXISTS idx_processed ON raw_tableau_files(processed);
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database initialized")
    
    def store_raw_json(self, file_name: str, json_data: Dict[str, Any]) -> int:
        """Store raw Tableau JSON in PostgreSQL"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO raw_tableau_files (file_name, raw_json)
            VALUES (%s, %s)
            ON CONFLICT (file_name) 
            DO UPDATE SET 
                raw_json = EXCLUDED.raw_json,
                created_at = CURRENT_TIMESTAMP,
                processed = FALSE
            RETURNING id;
        """, (file_name, Json(json_data)))
        
        file_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return file_id
    
    def get_raw_json(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve raw JSON by file ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT raw_json FROM raw_tableau_files WHERE id = %s;
        """, (file_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return result[0] if result else None
    
    def mark_as_processed(self, file_id: int):
        """Mark file as processed"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE raw_tableau_files 
            SET processed = TRUE 
            WHERE id = %s;
        """, (file_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
```

---

## 6. tools/__init__.py

```python
"""Tools package initialization"""
from .json_analyzer import analyze_json_hierarchy, get_entity_samples

__all__ = ["analyze_json_hierarchy", "get_entity_samples"]
```

---

## 7. tools/json_analyzer.py

```python
"""JSON structure analysis tools"""
from typing import Dict, Any, List
from langchain.tools import tool


@tool
def analyze_json_hierarchy(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze JSON structure depth-based.
    Level 1-2: Parents (no samples)
    Level 3+: Children (with 10 samples)
    
    Args:
        json_data: The JSON data to analyze
    
    Returns:
        Hierarchical structure with depth levels and samples
    """
    
    hierarchy = []
    
    def traverse(obj, path="root", level=0, parent_name=None):
        """Recursively traverse JSON structure"""
        
        if isinstance(obj, dict):
            entity_name = path.split('.')[-1]
            
            # Collect children names
            children = []
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    children.append(key)
            
            # Build entity info
            entity_info = {
                "level": level,
                "entity_name": entity_name,
                "entity_type": "parent" if level <= 2 else "child",
                "json_path": path,
                "parent_entity": parent_name,
                "children": children,
                "component_count": 1,
                "sample_data": None
            }
            
            # Add sample data for children (level 3+)
            if level >= 3:
                sample = {
                    k: v for k, v in obj.items() 
                    if not isinstance(v, (dict, list))
                }
                if sample:
                    entity_info["sample_data"] = [sample]
            
            hierarchy.append(entity_info)
            
            # Recurse into nested structures
            for key, value in obj.items():
                if isinstance(value, dict):
                    traverse(value, f"{path}.{key}", level + 1, entity_name)
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    # Array of objects
                    array_entity = {
                        "level": level + 1,
                        "entity_name": key,
                        "entity_type": "parent" if level + 1 <= 2 else "child",
                        "json_path": f"{path}.{key}[]",
                        "parent_entity": entity_name,
                        "children": list(value[0].keys()) if value else [],
                        "component_count": len(value),
                        "sample_data": None
                    }
                    
                    # Add samples for children (level 3+)
                    if level + 1 >= 3:
                        samples = []
                        for item in value[:10]:  # Max 10 samples
                            sample = {
                                k: v for k, v in item.items() 
                                if not isinstance(v, (dict, list))
                            }
                            if sample:
                                samples.append(sample)
                        array_entity["sample_data"] = samples
                    
                    hierarchy.append(array_entity)
                    
                    # Analyze first item for deeper nesting
                    if value:
                        traverse(value[0], f"{path}.{key}[]", level + 1, entity_name)
    
    traverse(json_data)
    
    return {
        "max_depth": max([e["level"] for e in hierarchy]) if hierarchy else 0,
        "total_entities": len(hierarchy),
        "hierarchy": hierarchy
    }


@tool
def get_entity_samples(json_data: Dict[str, Any], json_path: str, count: int = 10) -> List[Dict[str, Any]]:
    """
    Extract sample data from a specific JSON path.
    
    Args:
        json_data: The full JSON data
        json_path: Path to extract from (e.g., "root.dashboards[]")
        count: Number of samples to extract
    
    Returns:
        List of sample records
    """
    
    def navigate_path(obj, path_parts):
        if not path_parts or path_parts[0] == "root":
            path_parts = path_parts[1:] if len(path_parts) > 1 else []
        
        if not path_parts:
            return obj
        
        current = path_parts[0].replace('[]', '')
        remaining = path_parts[1:]
        
        if isinstance(obj, dict) and current in obj:
            value = obj[current]
            if isinstance(value, list):
                return value[:count]
            return navigate_path(value, remaining)
        
        return None
    
    parts = json_path.split('.')
    return navigate_path(json_data, parts) or []
```

---

## 8. agents/__init__.py

```python
"""Agents package initialization"""
from .workflow import create_workflow

__all__ = ["create_workflow"]
```

---

## 9. agents/prompts.py

```python
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

Generate complete DDL statements. Return ONLY valid JSON, no markdown or explanations.
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
```

---

## 10. agents/workflow.py

```python
"""LangGraph workflow with SQL Agent"""
from langgraph.graph import StateGraph, END
from langchain_google_vertexai import ChatVertexAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from typing import TypedDict, Dict, Any, List
import json

from tools.json_analyzer import analyze_json_hierarchy
from database.db_manager import DatabaseManager
from agents.prompts import SCHEMA_DESIGN_PROMPT, TRANSFORMATION_SQL_PROMPT
from config import (
    LLM_MODEL, 
    LLM_TEMPERATURE, 
    GOOGLE_CLOUD_PROJECT, 
    GOOGLE_CLOUD_LOCATION, 
    DB_CONFIG
)


class WorkflowState(TypedDict):
    """State for the workflow"""
    file_name: str
    raw_json: Dict[str, Any]
    file_id: int
    json_analysis: Dict[str, Any]
    relational_schema: Dict[str, Any]
    transformation_sql: Dict[str, Any]
    status: str
    errors: List[str]


def create_workflow():
    """Create the LangGraph workflow with SQL Agent"""
    
    # Initialize LLM
    llm = ChatVertexAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        project=GOOGLE_CLOUD_PROJECT,
        location=GOOGLE_CLOUD_LOCATION
    )
    
    # Initialize SQL Database connection
    db_uri = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    sql_db = SQLDatabase.from_uri(db_uri)
    
    # Create SQL Agent
    sql_agent = create_sql_agent(
        llm=llm,
        db=sql_db,
        agent_type="openai-tools",
        verbose=True
    )
    
    db_manager = DatabaseManager()
    
    # Node 1: Store raw JSON
    def store_raw_node(state: WorkflowState) -> WorkflowState:
        print(f"\n📥 Storing raw JSON for: {state['file_name']}")
        try:
            file_id = db_manager.store_raw_json(state['file_name'], state['raw_json'])
            state['file_id'] = file_id
            state['status'] = 'raw_stored'
            print(f"✅ Stored with ID: {file_id}")
        except Exception as e:
            state['status'] = 'error'
            state['errors'] = [f"Storage failed: {str(e)}"]
            print(f"❌ Error: {e}")
        return state
    
    # Node 2: Analyze JSON structure
    def analyze_structure_node(state: WorkflowState) -> WorkflowState:
        print(f"\n🔍 Analyzing JSON structure...")
        try:
            analysis = analyze_json_hierarchy.invoke({"json_data": state['raw_json']})
            state['json_analysis'] = analysis
            state['status'] = 'analyzed'
            print(f"✅ Found {analysis['total_entities']} entities, max depth: {analysis['max_depth']}")
        except Exception as e:
            state['status'] = 'error'
            state['errors'] = [f"Analysis failed: {str(e)}"]
            print(f"❌ Error: {e}")
        return state
    
    # Node 3: Design schema (Agent)
    def design_schema_node(state: WorkflowState) -> WorkflowState:
        print(f"\n🏗️  Designing relational schema...")
        try:
            prompt = SCHEMA_DESIGN_PROMPT.format(
                hierarchy=json.dumps(state['json_analysis'], indent=2)
            )
            
            response = llm.invoke(prompt)
            
            # Extract JSON from response
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            schema = json.loads(content)
            state['relational_schema'] = schema
            state['status'] = 'schema_designed'
            print(f"✅ Designed {len(schema['tables'])} tables")
        except Exception as e:
            state['status'] = 'error'
            state['errors'] = [f"Schema design failed: {str(e)}"]
            print(f"❌ Error: {e}")
        return state
    
    # Node 4: Create tables using SQL Agent
    def create_tables_node(state: WorkflowState) -> WorkflowState:
        print(f"\n🔨 Creating database tables using SQL Agent...")
        try:
            schema = state['relational_schema']
            
            # Combine all DDL statements
            all_ddl = []
            for table in schema['tables']:
                all_ddl.append(table['ddl'])
            all_ddl.extend(schema.get('indexes', []))
            
            ddl_combined = "\n".join(all_ddl)
            
            result = sql_agent.invoke({
                "input": f"""Execute these DDL statements to create the schema:
                
{ddl_combined}

Execute them in order and confirm when complete."""
            })
            
            state['status'] = 'tables_created'
            print(f"✅ Created {len(schema['tables'])} tables")
            print(f"Agent response: {result['output']}")
            
        except Exception as e:
            state['status'] = 'error'
            state['errors'] = [f"Table creation failed: {str(e)}"]
            print(f"❌ Error: {e}")
        return state
    
    # Node 5: Generate transformation SQL (Agent)
    def generate_transform_sql_node(state: WorkflowState) -> WorkflowState:
        print(f"\n⚙️  Generating SQL transformation queries...")
        try:
            prompt = TRANSFORMATION_SQL_PROMPT.format(
                schema=json.dumps(state['relational_schema'], indent=2),
                hierarchy=json.dumps(state['json_analysis'], indent=2)
            )
            
            response = llm.invoke(prompt)
            
            # Extract JSON from response
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            transform_sql = json.loads(content)
            state['transformation_sql'] = transform_sql
            state['status'] = 'transform_sql_ready'
            print(f"✅ Generated SQL for {len(transform_sql['transformations'])} tables")
        except Exception as e:
            state['status'] = 'error'
            state['errors'] = [f"Transform SQL generation failed: {str(e)}"]
            print(f"❌ Error: {e}")
        return state
    
    # Node 6: Execute transformations using SQL Agent
    def load_data_node(state: WorkflowState) -> WorkflowState:
        print(f"\n📊 Loading data using SQL Agent...")
        try:
            transformations = state['transformation_sql']['transformations']
            file_id = state['file_id']
            
            # Sort by order
            transformations.sort(key=lambda x: x.get('order', 999))
            
            # Build comprehensive instruction for SQL Agent
            sql_instructions = f"""Execute these SQL transformation queries in order to load data from raw_tableau_files (id={file_id}) into relational tables.

IMPORTANT: 
1. Execute queries in the exact order given
2. Replace :file_id with {file_id}
3. For queries with RETURNING clause, capture the returned ID and use it in subsequent queries
4. Track parent IDs: After each INSERT with RETURNING, store the ID to use in child table inserts

Here are the transformation queries:

"""
            
            for i, transform in enumerate(transformations, 1):
                sql_instructions += f"\n--- Query {i}: Load {transform['table_name']} ---\n"
                sql_instructions += f"{transform['sql']}\n"
            
            sql_instructions += """

Execute all queries and report:
1. How many rows were inserted into each table
2. Any errors encountered
3. Confirmation that data loading is complete
"""
            
            # Let SQL Agent handle everything
            result = sql_agent.invoke({"input": sql_instructions})
            
            print(f"✅ Data loading completed")
            print(f"Agent response: {result['output']}")
            
            db_manager.mark_as_processed(file_id)
            state['status'] = 'completed'
            
        except Exception as e:
            state['status'] = 'error'
            state['errors'] = [f"Data loading failed: {str(e)}"]
            print(f"❌ Error: {e}")
        return state
    
    # Build workflow graph
    workflow = StateGraph(WorkflowState)
    
    workflow.add_node("store_raw", store_raw_node)
    workflow.add_node("analyze", analyze_structure_node)
    workflow.add_node("design_schema", design_schema_node)
    workflow.add_node("create_tables", create_tables_node)
    workflow.add_node("generate_transform_sql", generate_transform_sql_node)
    workflow.add_node("load_data", load_data_node)
    
    workflow.set_entry_point("store_raw")
    workflow.add_edge("store_raw", "analyze")
    workflow.add_edge("analyze", "design_schema")
    workflow.add_edge("design_schema", "create_tables")
    workflow.add_edge("create_tables", "generate_transform_sql")
    workflow.add_edge("generate_transform_sql", "load_data")
    workflow.add_edge("load_data", END)
    
    return workflow.compile()
```

---

## 11. main.py

```python
"""Main entry point for Tableau Migration Accelerator"""
import xmltodict
import json
import sys
from pathlib import Path

from database.db_manager import DatabaseManager
from agents.workflow import create_workflow


def convert_xml_to_json(xml_file_path: str) -> dict:
    """Convert Tableau XML to JSON"""
    with open(xml_file_path, 'r', encoding='utf-8') as file:
        xml_content = file.read()
    
    json_data = xmltodict.parse(xml_content)
    return json_data


def main():
    """Main execution function"""
    
    print("=" * 60)
    print("🚀 Tableau Migration Accelerator with SQL Agent")
    print("=" * 60)
    
    # Initialize database
    print("\n1️⃣  Initializing database...")
    db = DatabaseManager()
    db.initialize_database()
    
    # Load Tableau XML file
    print("\n2️⃣  Loading Tableau XML...")
    
    # Check if file path provided as argument
    if len(sys.argv) > 1:
        xml_file_path = sys.argv[1]
    else:
        xml_file_path = "test_data/sample_tableau.xml"
    
    if not Path(xml_file_path).exists():
        print(f"❌ File not found: {xml_file_path}")
        print("Usage: python main.py <path_to_tableau_xml>")
        return
    
    json_data = convert_xml_to_json(xml_file_path)
    file_name = Path(xml_file_path).stem
    print(f"✅ Loaded XML file: {file_name}")
    
    # Create and run workflow
    print("\n3️⃣  Starting workflow...")
    workflow = create_workflow()
    
    result = workflow.invoke({
        "file_name": f"{file_name}.twb",
        "raw_json": json_data,
        "status": "started",
        "errors": []
    })
    
    # Print results
    print("\n" + "=" * 60)
    print("📋 WORKFLOW RESULTS")
    print("=" * 60)
    print(f"Status: {result['status']}")
    print(f"File ID: {result.get('file_id', 'N/A')}")
    
    if result.get('json_analysis'):
        analysis = result['json_analysis']
        print(f"Entities Found: {analysis.get('total_entities', 0)}")
        print(f"Max Depth: {analysis.get('max_depth', 0)}")
    
    if result.get('relational_schema'):
        schema = result['relational_schema']
        print(f"Tables Created: {len(schema.get('tables', []))}")
        for table in schema.get('tables', []):
            print(f"  - {table['table_name']}")
    
    if result.get('errors'):
        print(f"\n❌ Errors:")
        for error in result['errors']:
            print(f"  - {error}")
    else:
        print("\n✅ Process completed successfully!")
        print("\n💡 Next steps:")
        print("  - Query your relational tables for migration assessment")
        print("  - Run SQL queries to analyze Tableau complexity")
        print("  - Use the data for Looker migration planning")


if __name__ == "__main__":
    main()
```

---

## 12. README.md

```markdown
# Tableau Migration Accelerator

Automatically transform Tableau XML files into a queryable PostgreSQL relational database for migration assessment using LangGraph, SQL Agent, and Vertex AI Gemini.

## Features

- 🔄 Automatic XML to JSON conversion
- 📊 Depth-based JSON structure analysis
- 🤖 AI-powered schema design (Gemini 2.0 Flash)
- 🗄️ PostgreSQL native transformations using JSONB
- 🔧 SQL Agent for automated query execution
- 📈 Queryable relational model for migration assessment

## Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Google Cloud account with Vertex AI enabled
- Google Cloud CLI configured

## Setup

### 1. Google Cloud Setup

```bash
# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com
```

### 2. PostgreSQL Setup

```bash
# Install PostgreSQL (macOS)
brew install postgresql
brew services start postgresql

# Create database
createdb tableau_migration
```

### 3. Project Setup

```bash
# Clone/create project directory
mkdir tableau-sql-agent
cd tableau-sql-agent

# Copy all files from this guide

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 4. Environment Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
# Update: GOOGLE_CLOUD_PROJECT, DB_PASSWORD, etc.
```

## Usage

### Basic Usage

```bash
python main.py test_data/sample_tableau.xml
```

### Programmatic Usage

```python
from main import convert_xml_to_json
from agents.workflow import create_workflow

# Convert XML to JSON
json_data = convert_xml_to_json("my_tableau_file.xml")

# Run workflow
workflow = create_workflow()
result = workflow.invoke({
    "file_name": "my_tableau_file.twb",
    "raw_json": json_data,
    "status": "started",
    "errors": []
})

print(f"Status: {result['status']}")
```

## Architecture

```
Tableau XML → JSON → PostgreSQL Raw Storage
                ↓
         JSON Analysis (depth-based)
                ↓
         Schema Design (AI Agent)
                ↓
         Table Creation (SQL Agent)
                ↓
         Data Transform (SQL Agent with JSONB queries)
                ↓
         Relational Model (queryable for assessment)
```

## Assessment Queries

After processing, query the relational tables:

```sql
-- Find all dashboards
SELECT * FROM dashboard;

-- Count calculated fields by type
SELECT calculation_type, COUNT(*) 
FROM calculated_field 
GROUP BY calculation_type;

-- Migration complexity by workbook
SELECT 
    w.workbook_name,
    COUNT(DISTINCT d.dashboard_id) as dashboard_count,
    COUNT(cf.field_id) as calc_field_count
FROM workbook w
LEFT JOIN dashboard d ON w.workbook_id = d.workbook_id
LEFT JOIN calculated_field cf ON w.workbook_id = cf.workbook_id
GROUP BY w.workbook_name;
```

## Development

### Run Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black .
ruff check .
```

## Troubleshooting

### Connection Issues

- Verify PostgreSQL is running: `pg_isready`
- Check credentials in `.env`
- Test connection: `psql -U postgres -d tableau_migration`

### Google Cloud Authentication

```bash
# Re-authenticate
gcloud auth application-default login

# Verify project
gcloud config get-value project
```

### SQL Agent Errors

- Check PostgreSQL JSONB support (v9.4+)
- Verify table permissions
- Review SQL Agent verbose output

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
```

---

## Setup Instructions

### Step 1: Create Project Directory

```bash
mkdir tableau-sql-agent
cd tableau-sql-agent
```

### Step 2: Copy All Files

Copy all the code sections above into their respective files.

### Step 3: Google Cloud Setup

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable aiplatform.googleapis.com
```

### Step 4: PostgreSQL Setup

```bash
# macOS
brew install postgresql
brew services start postgresql
createdb tableau_migration

# Ubuntu/Debian
sudo apt-get install postgresql
sudo -u postgres createdb tableau_migration
```

### Step 5: Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

### Step 6: Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### Step 7: Run

```bash
python main.py test_data/sample_tableau.xml
```

---

## Key Benefits

✅ **Depth-Based Analysis** - Level 1-2: parents (no samples), Level 3+: children (10 samples)
✅ **PostgreSQL Native** - Uses JSONB queries for transformation
✅ **SQL Agent** - Automatic query generation and execution
✅ **Vertex AI Gemini** - Cost-effective AI with Google Cloud integration
✅ **Queryable Model** - SQL-based migration assessment
✅ **Scalable** - Handle 100s of Tableau files

---

## Testing Checklist

- [ ] PostgreSQL connection works
- [ ] Google Cloud authentication configured
- [ ] Raw JSON storage successful
- [ ] JSON hierarchy analysis completes
- [ ] Schema design generates DDL
- [ ] Tables created via SQL Agent
- [ ] Data loaded successfully
- [ ] Query relational tables works

---

## Next Steps

1. Test with sample Tableau XML file
2. Verify schema design quality
3. Run assessment queries
4. Iterate on schema if needed
5. Scale to multiple Tableau files
6. Build migration assessment dashboard
